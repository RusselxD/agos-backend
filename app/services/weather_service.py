from datetime import datetime, timezone, timedelta
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

            # Step 1: Fetch weather data from external API
            # weather_code, precipitation = await self._fetch_weather(db=db, sensor_id=sensor_id)
            weather_conditions: list[WeatherCreate] = await self._fetch_weather(db=db)

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
            raise HTTPException(status_code=404, detail="No location coordinates found")

        weather_conditions: list[WeatherCreate] = []
        async with httpx.AsyncClient() as client:
            for coord in coordinates:

                lat = coord.latitude
                lon = coord.longitude

                api_url = (
                    f"https://api.open-meteo.com/v1/forecast?"
                    f"latitude={lat}&longitude={lon}&"
                    f"current=precipitation,weather_code,temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,cloud_cover"
                )

                try:
                    response = await client.get(api_url, timeout=20)
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
                except httpx.HTTPError as e:
                    raise HTTPException(status_code=500, detail=f"Error fetching weather data: {str(e)}")
        return weather_conditions


    async def _save_fetched_weather_and_return(self, db: AsyncSession, weather_data: WeatherCreate) -> Weather:
        return await weather_crud.create_and_return(db=db, obj_in=weather_data)


    async def _save_fetched_weather(self, db: AsyncSession, weather_data: WeatherCreate) -> None:
        await weather_crud.create_only(db=db, obj_in=weather_data)


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
            condition=self._get_weather_condition(weather.weather_code),
            precipitation_description=self._get_weather_description(weather.precipitation_mm),
            temperature_description=self._get_temperature_description(weather.temperature_2m),
            humidity_level=self._get_humidity_level(weather.relative_humidity_2m),
            wind_category=self._get_wind_category(weather.wind_speed_10m),
            wind_direction_label=self._get_wind_direction_label(weather.wind_direction_10m),
            cloudiness=self._get_cloudiness(weather.cloud_cover),
            comfort_level=self._get_comfort_level(weather.temperature_2m, weather.relative_humidity_2m),
            storm_risk_level=self._get_storm_risk_level(weather.weather_code, weather.precipitation_mm, weather.wind_speed_10m)
        )


    # --- Dynamic value generators ---

    def _get_temperature_description(self, temperature_c: float) -> str:
        if temperature_c < 15:
            return "Cold"
        elif temperature_c < 22:
            return "Cool"
        elif temperature_c < 30:
            return "Warm"
        else:
            return "Hot"


    def _get_humidity_level(self, humidity_percent: float) -> str:
        if humidity_percent < 40:
            return "Dry"
        elif humidity_percent < 60:
            return "Comfortable"
        elif humidity_percent < 80:
            return "Humid"
        else:
            return "Very humid"


    def _get_wind_category(self, wind_speed_kmh: float) -> str:
        if wind_speed_kmh < 5:
            return "Calm"
        elif wind_speed_kmh < 15:
            return "Light breeze"
        elif wind_speed_kmh < 30:
            return "Breezy"
        elif wind_speed_kmh < 50:
            return "Strong winds"
        else:
            return "High winds"


    def _get_wind_direction_label(self, degrees: float) -> str:
        # Normalize degrees to 0-360
        degrees = degrees % 360
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        # Each direction covers 45 degrees, offset by 22.5 to center
        index = int((degrees + 22.5) / 45) % 8
        return directions[index]


    def _get_cloudiness(self, cloud_cover_percent: float) -> str:
        if cloud_cover_percent < 20:
            return "Clear"
        elif cloud_cover_percent < 50:
            return "Partly cloudy"
        elif cloud_cover_percent < 80:
            return "Mostly cloudy"
        else:
            return "Overcast"


    def _get_comfort_level(self, temperature_c: float, humidity_percent: float) -> str:
        # Simplified heat index / comfort assessment
        if temperature_c < 15:
            return "Cool"
        elif temperature_c < 22:
            if humidity_percent > 70:
                return "Cool & damp"
            return "Comfortable"
        elif temperature_c < 28:
            if humidity_percent < 50:
                return "Comfortable"
            elif humidity_percent < 70:
                return "Warm & humid"
            else:
                return "Uncomfortable"
        elif temperature_c < 35:
            if humidity_percent < 40:
                return "Hot but tolerable"
            elif humidity_percent < 60:
                return "Uncomfortable"
            else:
                return "Oppressive"
        else:
            if humidity_percent > 50:
                return "Heat stress risk"
            return "Very hot"


    def _get_storm_risk_level(self, weather_code: int, precipitation_mm: float, wind_speed_kmh: float) -> str:
        # Thunderstorm codes: 95-99
        is_thunderstorm = 95 <= weather_code <= 99
        heavy_rain = precipitation_mm > 10
        strong_wind = wind_speed_kmh > 30
        
        if is_thunderstorm:
            return "Likely"
        elif heavy_rain and strong_wind:
            return "Possible"
        elif heavy_rain or (80 <= weather_code <= 82 and strong_wind):
            return "Low"
        else:
            return "None"


weather_service = WeatherService()