from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.system_settings import SensorConfigResponse
from app.crud.system_settings import system_settings as system_settings_crud

class CacheService:

    def __init__(self):
        self._sensor_config_cache: Optional[SensorConfigResponse] = None  # cached sensor configuration
        self._cache_timestamp: Optional[datetime] = None                  # timestamp of when the cache was last updated
        self._cache_ttl_timedelta = timedelta(minutes=60)                 # defines how long the cache is valid (Time To Live)

    async def get_sensor_config(self, db: AsyncSession) -> SensorConfigResponse:
        now = datetime.now()

        # Return cached config if still valid
        if (self._sensor_config_cache and self._cache_timestamp and now - self._cache_timestamp < self._cache_ttl_timedelta):
            return self._sensor_config_cache
        
        sensor_config_data = await system_settings_crud.get_value(db, key="sensor_config")
        self._sensor_config_cache = SensorConfigResponse.model_validate(sensor_config_data)
        self._cache_timestamp = now
        return self._sensor_config_cache

cache_service = CacheService()