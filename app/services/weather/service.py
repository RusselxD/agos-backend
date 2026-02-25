import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.state import fusion_state_manager
from app.schemas import (
    WeatherStatus,
    WeatherWebSocketResponse,
)
from app.schemas.weather import WeatherComprehensiveResponse, WeatherConditionResponse
from app.utils.weather_mappers import *

from .api_client import fetch_weather_for_coordinates
from .persistence import save_weather, save_weather_and_return
from app.services.cache_service import cache_service
from app.crud import weather_crud


logger = logging.getLogger(__name__)


class WeatherService:

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=settings.APP_TIMEZONE)


    async def start(self) -> None:
        """Fetch initial weather and start the hourly scheduler."""
        async with AsyncSessionLocal() as db:
            try:
                await self._fetch_initial_weather(db=db, location_id=1)
            except Exception:
                logger.exception("Initial weather fetch failed during startup")

        self.scheduler.add_job(
            self._fetch_and_update_weather,
            CronTrigger(minute=0, timezone=settings.APP_TIMEZONE),
            id="fetch_weather_condition_job",
        )
        self.scheduler.start()
        print("✅ Weather service scheduler started.")


    async def stop(self) -> None:
        self.scheduler.shutdown()
        print("✅ Weather service scheduler stopped.")


    async def _fetch_initial_weather(self, db: AsyncSession, location_id: int) -> None:
        latest_weather = await weather_crud.get_latest_weather(db=db, location_id=location_id)
        stale_threshold = datetime.now(timezone.utc) - timedelta(
            minutes=settings.WEATHER_CONDITION_WARNING_PERIOD_MINUTES
        )

        if not latest_weather or latest_weather["created_at"] < stale_threshold:
            print("⚠️ Initial weather data missing or stale. Fetching new data...")
            coordinates = await cache_service.get_all_location_coordinates(db=db)
            if not coordinates:
                raise RuntimeError("No location coordinates found")

            weather_conditions = await fetch_weather_for_coordinates(coordinates)
            for condition in weather_conditions:
                await save_weather(db=db, weather_data=condition)
            print("✅ Initial weather data fetched and saved.")
        else:
            print("✅ Initial weather data is up-to-date. No fetch needed.")


    async def _fetch_and_update_weather(self) -> None:
        """Scheduled job: fetch weather, save, broadcast via WebSocket, update fusion state."""
        from app.services.websocket_service import websocket_service

        async with AsyncSessionLocal() as db:
            try:
                coordinates = await cache_service.get_all_location_coordinates(db=db)
                if not coordinates:
                    logger.warning("No location coordinates found; skipping weather update")
                    return

                weather_conditions = await fetch_weather_for_coordinates(coordinates)
            except Exception:
                logger.exception("Scheduled weather fetch/update failed")
                return

            if not weather_conditions:
                logger.warning("Scheduled weather fetch returned no data; skipping update cycle")
                return

            for condition in weather_conditions:
                db_obj = await save_weather_and_return(db=db, weather_data=condition)

                weather_summary = self.get_weather_summary(
                    created_at=db_obj.created_at,
                    weather_code=condition.weather_code,
                    precipitation_mm=condition.precipitation_mm,
                )

                weather_data = WeatherWebSocketResponse(
                    status="success",
                    message="Retrieved successfully",
                    weather_condition=weather_summary,
                )
                await websocket_service.broadcast_update(
                    update_type="weather_update",
                    data=weather_data.model_dump(mode="json"),
                    location_id=condition.location_id,
                )

                await fusion_state_manager.recalculate_weather_score(
                    weather_status=WeatherStatus(
                        timestamp=db_obj.created_at,
                        precipitation_mm=condition.precipitation_mm,
                        weather_condition=weather_summary.condition,
                    ),
                    location_id=condition.location_id,
                )


    def get_weather_summary(
        self, created_at: datetime, weather_code: int, precipitation_mm: float
    ) -> WeatherConditionResponse:
        return WeatherConditionResponse(
            precipitation_mm=precipitation_mm,
            weather_code=weather_code,
            timestamp=created_at,
            condition=get_weather_condition(weather_code),
            description=get_weather_description(precipitation_mm),
        )


    async def get_latest_comprehensive_weather_summary(
        self, db: AsyncSession, location_id: int
    ) -> WeatherComprehensiveResponse:
        weather = await weather_crud.get_latest_weather_full(db=db, location_id=location_id)
        if not weather:
            raise HTTPException(status_code=404, detail="No weather data found for this location")

        return WeatherComprehensiveResponse(
            timestamp=weather.created_at,
            precipitation_mm=weather.precipitation_mm,
            weather_code=weather.weather_code,
            temperature_c=weather.temperature_2m,
            humidity_percent=weather.relative_humidity_2m,
            wind_speed_kmh=weather.wind_speed_10m,
            wind_direction_degrees=weather.wind_direction_10m,
            cloud_cover_percent=weather.cloud_cover,
            condition=get_weather_condition(weather.weather_code),
            precipitation_description=get_weather_description(weather.precipitation_mm),
            temperature_description=get_temperature_description(weather.temperature_2m),
            humidity_level=get_humidity_level(weather.relative_humidity_2m),
            wind_category=get_wind_category(weather.wind_speed_10m),
            wind_direction_label=get_wind_direction_label(weather.wind_direction_10m),
            cloudiness=get_cloudiness(weather.cloud_cover),
            comfort_level=get_comfort_level(weather.temperature_2m, weather.relative_humidity_2m),
            storm_risk_level=get_storm_risk_level(
                weather.weather_code, weather.precipitation_mm, weather.wind_speed_10m
            ),
        )


weather_service = WeatherService()
