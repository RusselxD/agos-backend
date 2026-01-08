from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import SensorConfigResponse, AlertThresholdsResponse
from app.crud.system_settings import system_settings as system_settings_crud
from app.crud.sensor_devices import sensor_device as sensor_device_crud

class CacheService:

    def __init__(self):
        self._sensor_coords_cache: Optional[tuple[float, float]] = None  # cached sensor coordinates
        self._sensor_config_cache: Optional[SensorConfigResponse] = None  # cached sensor configuration
        self._alert_thresholds_cache: Optional[AlertThresholdsResponse] = None  # cached alert thresholds

        self._cache_timestamp: Optional[datetime] = None                  # timestamp of when the cache was last updated
        self._cache_ttl_timedelta = timedelta(hours=24)                 # defines how long the cache is valid (Time To Live)

    async def update_alert_thresholds_cache(self, db: AsyncSession) -> None:
        alert_thresholds_data = await system_settings_crud.get_value(db=db, key="alert_thresholds")
        self._alert_thresholds_cache = AlertThresholdsResponse.model_validate(alert_thresholds_data)
        self._cache_timestamp = datetime.now()

    async def update_sensor_config_cache(self, db: AsyncSession) -> None:
        sensor_config_data = await system_settings_crud.get_value(db=db, key="sensor_config")
        self._sensor_config_cache = SensorConfigResponse.model_validate(sensor_config_data)
        self._cache_timestamp = datetime.now()

    async def update_sensor_coords_cache(self, db: AsyncSession, sensor_id: int = 1) -> None:
        sensor_coords_data = await sensor_device_crud.get_coordinates(db=db, sensor_id=sensor_id)
        self._sensor_coords_cache = sensor_coords_data
        self._cache_timestamp = datetime.now()

    async def get_sensor_config(self, db: AsyncSession) -> SensorConfigResponse:
        now = datetime.now()

        # Return cached config if still valid
        if (self._sensor_config_cache and self._cache_timestamp and now - self._cache_timestamp < self._cache_ttl_timedelta):
            return self._sensor_config_cache
        
        await self.update_sensor_config_cache(db=db)
        return self._sensor_config_cache

    async def get_sensor_coords(self, db: AsyncSession, sensor_id: int = 1) -> tuple[float, float]:
        now = datetime.now()

        # Return cached coordinates if still valid
        if (self._sensor_coords_cache and self._cache_timestamp and now - self._cache_timestamp < self._cache_ttl_timedelta):
            return self._sensor_coords_cache

        await self.update_sensor_coords_cache(db=db, sensor_id=sensor_id)
        return self._sensor_coords_cache

    async def get_alert_thresholds(self, db: AsyncSession) -> AlertThresholdsResponse:
        now = datetime.now()

        # Return cached thresholds if still valid
        if (self._alert_thresholds_cache and self._cache_timestamp and now - self._cache_timestamp < self._cache_ttl_timedelta):
            return self._alert_thresholds_cache
        
        await self.update_alert_thresholds_cache(db=db)
        return self._alert_thresholds_cache

cache_service = CacheService()