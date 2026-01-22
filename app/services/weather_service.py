from datetime import datetime, timezone, timedelta
import httpx
from fastapi import HTTPException
from app.models import Weather
from app.schemas import WeatherCreate, WeatherStatus, WeatherWebSocketResponse, WeatherConditionResponse, LocationCoordinate
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.cache_service import cache_service
from app.crud.weather import weather as weather_crud
from app.core.config import settings
from app.core.state import fusion_state_manager
from fastapi import Depends
from app.core.database import get_db
from app.core.database import AsyncSessionLocal

class WeatherService:

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    async def start(self):

        # Fetch initial weather data on startup
        async with AsyncSessionLocal() as db:
            await self._fetch_initial_weather(db=db, location_id=1) # hardcoded 1, this is for initial anyway, the _periodic job will take care of the rest

        """Start the scheduler with jobs."""
        self.scheduler.add_job(
            self._fetch_and_update_weather,
            CronTrigger(minute=0), # Every hour at minute 0
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
                await self._save_fetched_weather(db=db, location_id=condition.location_id, precipitation_mm=condition.precipitation_mm, weather_code=condition.weather_code)
            
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

            # Step 1: Fetch weather data from external API
            # weather_code, precipitation = await self._fetch_weather(db=db, sensor_id=sensor_id)
            weather_conditions: list[WeatherCreate] = await self._fetch_weather(db=db)

            for condition in weather_conditions:

                # Step 2: Save fetched data to the database
                db_obj: Weather = await self._save_fetched_weather_and_return(db=db, location_id=condition.location_id, precipitation_mm=condition.precipitation_mm, weather_code=condition.weather_code)

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

                )

    async def _fetch_weather(self, db: AsyncSession) -> list[WeatherCreate]:

        # Get sensor device coordinates from cache service
        # lat, lon = await cache_service.get_sensor_coords(db=db, sensor_id=sensor_id)
        coordinates: list[LocationCoordinate] = await cache_service.get_all_location_coordinates(db=db)

        if not coordinates:
            raise HTTPException(status_code=404, detail="No location coordinates found")

        weather_conditions: list[WeatherCreate] = []
        async with httpx.AsyncClient() as client:
            for coord in coordinates:

                lat = coord.latitude
                lon = coord.longitude

                api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=precipitation,weather_code"

                try:
                    response = await client.get(api_url, timeout=20)
                    response.raise_for_status()  # Raises exception for 4xx/5xx status codes
                    data = response.json()
                    weather_conditions.append(
                        WeatherCreate(
                            location_id=coord.id,
                            precipitation_mm=data["current"]["precipitation"],
                            weather_code=data["current"]["weather_code"]
                        ))
                except httpx.HTTPError as e:
                    raise HTTPException(status_code=500, detail=f"Error fetching weather data: {str(e)}")
        return weather_conditions

    async def _save_fetched_weather_and_return(self, db: AsyncSession, location_id: int, precipitation_mm: float, weather_code: int) -> Weather:
        obj_in = WeatherCreate(
            location_id=location_id,
            precipitation_mm=precipitation_mm,
            weather_code=weather_code
        )

        return await weather_crud.create_and_return(db=db, obj_in=obj_in)

    async def _save_fetched_weather(self, db: AsyncSession, location_id: int, precipitation_mm: float, weather_code: int) -> None:
        obj_in = WeatherCreate(
            location_id=location_id,
            precipitation_mm=precipitation_mm,
            weather_code=weather_code
        )
        await weather_crud.create_only(db=db, obj_in=obj_in)

    def _get_weather_condition(self, weather_code: int) -> str:
        if weather_code == 0: # Clear sky
            return "Sunny"
        elif weather_code == 1:
            return "Mainly Clear"
        
        elif 2 <= weather_code <= 3: # Cloudy
            return "Cloudy"
    
        elif 45 <= weather_code <= 48: # Fog
            return "Foggy"
        
        elif 51 <= weather_code <= 57: # Drizzle
            return "Drizzle"
        
        elif 61 <= weather_code <= 67: # Rain
            return "Rain"
        
        elif 71 <= weather_code <= 77: # Snow
            return "Snow"
        
        elif 80 <= weather_code <= 82: # Rain showers
            return "Showers"
        
        elif 85 <= weather_code <= 86: # Snow showers
            return "Snow Showers"
        
        elif 95 <= weather_code <= 99: # Thunderstorm
            return "Thunderstorm"
        
        return "Unknown"

    def _get_weather_description(self, precipitation: float) -> str:
        if precipitation == 0:
            return "No rainfall detected"
        elif precipitation <= 2.5:
            return "Light precipitation"
        elif precipitation <= 10:
            return "Moderate rainfall intensity"
        elif precipitation <= 50:
            return "Heavy rainfall detected"
        else:
            return "Extreme rainfall conditions"

    def get_weather_summary(self, created_at: datetime, weather_code: int, precipitation_mm: float) -> WeatherConditionResponse:
        return WeatherConditionResponse(
            precipitation_mm=precipitation_mm,
            weather_code=weather_code,
            timestamp=created_at,
            condition = self._get_weather_condition(weather_code),
            description = self._get_weather_description(precipitation_mm)
        )

weather_service = WeatherService()