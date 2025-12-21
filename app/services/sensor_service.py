from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.schemas.system_settings import SensorConfigResponse
from datetime import datetime, timedelta, timezone
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud
from app.crud.sensor_devices import sensor_device as sensor_device_crud
from app.schemas.sensor_reading import SensorReadingResponse, SensorReadingCreate, SensorReadingPaginatedResponse, SensorDataRecordedResponse
from app.crud.system_settings import system_settings as system_settings_crud

class SensorService:

    def __init__(self):
        self._sensor_config_cache: Optional[SensorConfigResponse] = None  # cached sensor configuration
        self._cache_timestamp: Optional[datetime] = None                  # timestamp of when the cache was last updated
        self._cache_ttl_timedelta = timedelta(minutes=60)                 # defines how long the cache is valid (Time To Live)

    async def _get_sensor_config(self, db: AsyncSession) -> SensorConfigResponse:
        now = datetime.now()

        # Return cached config if still valid
        if (self._sensor_config_cache and self._cache_timestamp and now - self._cache_timestamp < self._cache_ttl_timedelta):
            return self._sensor_config_cache
        
        sensor_config_data = await system_settings_crud.get_value(db, key="sensor_config")
        self._sensor_config_cache = SensorConfigResponse.model_validate(sensor_config_data)
        self._cache_timestamp = now
        return self._sensor_config_cache

    async def record_reading(self, db: AsyncSession, obj_in: SensorReadingCreate) -> SensorDataRecordedResponse:
        
        # Verify sensor device exists
        if not await sensor_device_crud.get(db, id=obj_in.sensor_id):
            return SensorDataRecordedResponse(timestamp=datetime.now(timezone.utc), status="Error: Sensor device not found")

        # Get cached sensor installation height and calculate water level
        sensor_height = (await self._get_sensor_config(db)).installation_height
        water_level_cm = sensor_height - obj_in.raw_distance_cm

        # Save to database
        db_reading = await sensor_reading_crud.create_record(
            db, obj_in=obj_in, water_level_cm=water_level_cm
        )

            # await ws_manager.broadcast({
    #     "type": "sensor_update",
    #     "data": record_ack.status
    # })

        return SensorDataRecordedResponse(timestamp=db_reading.created_at, status="Success: Reading recorded")


sensor_service = SensorService()