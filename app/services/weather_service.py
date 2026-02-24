from datetime import datetime, timezone, timedelta
import logging
import httpx
from fastapi import HTTPException
from app.models import Weather
from app.schemas import WeatherCreate, WeatherStatus, WeatherWebSocketResponse, WeatherConditionResponse, WeatherComprehensiveResponse, LocationCoordinate
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.cache_service import cache_service
from app.crud import weather_crud
from app.core.config import settings
from app.core.state import fusion_state_manager
from fastapi import Depends
from app.core.database import get_db
from app.core.database import AsyncSessionLocal
from app.utils.weather_mappers import *


logger = logging.getLogger(__name__)


class WeatherService:

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=settings.APP_TIMEZONE)


    async def start(self):

        # Fetch initial weather data on startup
        async with AsyncSessionLocal() as db:
            try:
                await self._fetch_initial_weather(db=db, location_id=1) # hardcoded 1, this is for initial anyway, the _periodic job will take care of the rest
            except Exception:
                logger.exception("Initial weather fetch failed during startup")

        """Start the scheduler with jobs."""
        self.scheduler.add_job(
            self._fetch_and_update_weather,
            CronTrigger(minute=0, timezone=settings.APP_TIMEZONE), # Every hour at minute 0 (configured timezone)
            id="fetch_weather_condition_job",
        )
        self.scheduler.start()
        print("✅ Weather service scheduler started.")


    async def stop(self):
        self.scheduler.shutdown()
        print("✅ Weather service scheduler stopped.")


    async def _fetch_initial_weather(self, db: AsyncSession, location_id: int):

        latest_weather = await weather_crud.get_latest_weather(db=db, location_id=location_id)

        # Check if latest weather data is missing or stale
        if not latest_weather or (latest_weather["created_at"] < datetime.now(timezone.utc) - timedelta(minutes=settings.WEATHER_CONDITION_WARNING_PERIOD_MINUTES)):
            
            print("⚠️ Initial weather data missing or stale. Fetching new data...")
            # Fetch weather data from external API
            weather_conditions: list[WeatherCreate] = await self._fetch_weather(db=db)

            for condition in weather_conditions:

                # Save fetched data to the database
                await self._save_fetched_weather(db=db, weather_data=condition)
            
            print("✅ Initial weather data fetched and saved.")
        else:
            print("✅ Initial weather data is up-to-date. No fetch needed.")


    """
        This function is called periodically by the scheduler.
        
        This function fetches weather data from an external API, saves it to the database,
        prepares a summary response, broadcasts via WebSocket, and updates fusion analysis state.
    
    """
    async def _fetch_and_update_weather(self, db: AsyncSession = Depends(get_db)):
        from app.services.websocket_service import websocket_service

        async with AsyncSessionLocal() as db:
            try:
                # Step 1: Fetch weather data from external API
                # weather_code, precipitation = await self._fetch_weather(db=db, sensor_id=sensor_id)
                weather_conditions: list[WeatherCreate] = await self._fetch_weather(db=db)
            except Exception:
                # Do not raise HTTPException from a background scheduler job.
                logger.exception("Scheduled weather fetch/update failed")
                return

            if not weather_conditions:
                logger.warning("Scheduled weather fetch returned no data; skipping update cycle")
                return

            for condition in weather_conditions:

                # Step 2: Save fetched data to the database
                db_obj: Weather = await self._save_fetched_weather_and_return(db=db, weather_data=condition)

                # Step 3: Prepare summary response
                weather_summary = self.get_weather_summary(created_at=db_obj.created_at, weather_code=condition.weather_code, precipitation_mm=condition.precipitation_mm)
                
                # Step 4: Websocket broadcast
                weather_data = WeatherWebSocketResponse(
                    status="success",
                    message="Retrieved successfully",
                    weather_condition=weather_summary
                )

                await websocket_service.broadcast_update(
                    update_type="weather_update",
                    data=weather_data.model_dump(mode='json'),
                    location_id=condition.location_id
                )

                # Step 5: Update fusion analysis state
                await fusion_state_manager.recalculate_weather_score(
                    weather_status=WeatherStatus(
                        timestamp=db_obj.created_at,
                        precipitation_mm=condition.precipitation_mm,
                        weather_condition=weather_summary.condition
                    ), 
                    location_id=condition.location_id
                )


    async def _fetch_weather(self, db: AsyncSession) -> list[WeatherCreate]:

        # Get sensor device coordinates from cache service
        coordinates: list[LocationCoordinate] = await cache_service.get_all_location_coordinates(db=db)

        if not coordinates:
            raise RuntimeError("No location coordinates found")

        weather_conditions: list[WeatherCreate] = []
        timeout = httpx.Timeout(20.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for coord in coordinates:

                lat = coord.latitude
                lon = coord.longitude

                api_url = (
                    f"https://api.open-meteo.com/v1/forecast?"
                    f"latitude={lat}&longitude={lon}&"
                    f"current=precipitation,weather_code,temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,cloud_cover"
                )

                last_error: Exception | None = None
                for attempt in range(1, 3):
                    try:
                        response = await client.get(api_url)
                        response.raise_for_status()  # Raises exception for 4xx/5xx status codes
                        data = response.json()
                        current = data["current"]
                        weather_conditions.append(
                            WeatherCreate(
                                location_id=coord.id,
                                precipitation_mm=current["precipitation"],
                                weather_code=current["weather_code"],
                                temperature_2m=current["temperature_2m"],
                                relative_humidity_2m=current["relative_humidity_2m"],
                                wind_speed_10m=current["wind_speed_10m"],
                                wind_direction_10m=current["wind_direction_10m"],
                                cloud_cover=current["cloud_cover"]
                            ))
                        last_error = None
                        break
                    except httpx.TimeoutException as e:
                        last_error = e
                        logger.warning(
                            "Weather API timeout for location_id=%s (attempt %s/2)",
                            coord.id,
                            attempt,
                        )
                    except httpx.HTTPStatusError as e:
                        last_error = e
                        logger.warning(
                            "Weather API returned %s for location_id=%s (attempt %s/2)",
                            e.response.status_code,
                            coord.id,
                            attempt,
                        )
                        if e.response.status_code < 500:
                            break
                    except httpx.HTTPError as e:
                        last_error = e
                        logger.warning(
                            "Weather API request failed for location_id=%s: %s",
                            coord.id,
                            type(e).__name__,
                        )
                        break

                if last_error is not None:
                    logger.error(
                        "Skipping weather fetch for location_id=%s after failure: %s",
                        coord.id,
                        type(last_error).__name__,
                    )

        if not weather_conditions:
            raise RuntimeError("Weather fetch failed for all locations")
        return weather_conditions


    async def _save_fetched_weather_and_return(self, db: AsyncSession, weather_data: WeatherCreate) -> Weather:
        return await weather_crud.create_and_return(db=db, obj_in=weather_data)


    async def _save_fetched_weather(self, db: AsyncSession, weather_data: WeatherCreate) -> None:
        await weather_crud.create_only(db=db, obj_in=weather_data)


    def get_weather_summary(self, created_at: datetime, weather_code: int, precipitation_mm: float) -> WeatherConditionResponse:
        return WeatherConditionResponse(
            precipitation_mm=precipitation_mm,
            weather_code=weather_code,
            timestamp=created_at,
            condition = get_weather_condition(weather_code),
            description = get_weather_description(precipitation_mm)
        )


    async def get_latest_comprehensive_weather_summary(self, db: AsyncSession, location_id: int) -> WeatherComprehensiveResponse:
        
        weather = await weather_crud.get_latest_weather_full(db=db, location_id=location_id)
        
        if not weather:
            raise HTTPException(status_code=404, detail="No weather data found for this location")
        
        return WeatherComprehensiveResponse(
            timestamp=weather.created_at,
            # Raw values
            precipitation_mm=weather.precipitation_mm,
            weather_code=weather.weather_code,
            temperature_c=weather.temperature_2m,
            humidity_percent=weather.relative_humidity_2m,
            wind_speed_kmh=weather.wind_speed_10m,
            wind_direction_degrees=weather.wind_direction_10m,
            cloud_cover_percent=weather.cloud_cover,
            # Derived values
            condition=get_weather_condition(weather.weather_code),
            precipitation_description=get_weather_description(weather.precipitation_mm),
            temperature_description=get_temperature_description(weather.temperature_2m),
            humidity_level=get_humidity_level(weather.relative_humidity_2m),
            wind_category=get_wind_category(weather.wind_speed_10m),
            wind_direction_label=get_wind_direction_label(weather.wind_direction_10m),
            cloudiness=get_cloudiness(weather.cloud_cover),
            comfort_level=get_comfort_level(weather.temperature_2m, weather.relative_humidity_2m),
            storm_risk_level=get_storm_risk_level(weather.weather_code, weather.precipitation_mm, weather.wind_speed_10m)
        )


weather_service = WeatherService()
