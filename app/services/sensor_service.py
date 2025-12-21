from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.models.sensor_readings import SensorReading
from app.schemas.system_settings import SensorConfigResponse
from datetime import datetime, timedelta, timezone
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud
from app.crud.sensor_devices import sensor_device as sensor_device_crud
from app.schemas.sensor_reading import SensorReadingResponse, SensorReadingCreate, SensorReadingPaginatedResponse, SensorDataRecordedResponse
from app.crud.system_settings import system_settings as system_settings_crud

class SensorReadingService:

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

    async def get_items_paginated(self, db: AsyncSession, page: int = 1, page_size: int = 10) -> SensorReadingPaginatedResponse:
        
        db_items = await sensor_reading_crud.get_items_paginated(db, page=page, page_size=page_size)
        
        items = []
        # Process each item to determine status and change rate
        for item in db_items[:page_size]:
            if item.prev_water_level is None:
                change_rate = 0
                status = "stable"
            else:
                change_rate = round(item.water_level_cm - item.prev_water_level, 2)
            
                if change_rate > 1:
                    status = 'rising'
                elif change_rate < -1:
                    status = 'falling'
                else:
                    status = 'stable'

            items.append(SensorReadingResponse(
                id=item.id,
                timestamp=item.timestamp,
                water_level_cm=item.water_level_cm,
                status=status,
                change_rate=change_rate
            ))

        has_more = len(db_items) > page_size
        return SensorReadingPaginatedResponse(items=items[:page_size], has_more=has_more)

    async def record_reading(self, db: AsyncSession, obj_in: SensorReadingCreate) -> SensorDataRecordedResponse:
        
        # Verify sensor device exists
        if not await sensor_device_crud.get(db, id=obj_in.sensor_id):
            return SensorDataRecordedResponse(timestamp=datetime.now(timezone.utc), status="Error: Sensor device not found")

        # Get cached sensor installation height and calculate water level
        sensor_height = (await self._get_sensor_config(db)).installation_height
        water_level_cm = sensor_height - obj_in.raw_distance_cm

        # Convert Pydantic model to dict
        data = obj_in.model_dump()

        # Create SensorReading DB object
        db_obj = SensorReading(**data)
        db_obj.water_level_cm = water_level_cm

        # Save to database
        db_reading = await sensor_reading_crud.create_record(
            db, db_obj=db_obj,
        )

        # TODO: Broadcast via WebSocket to connected clients
        # await ws_manager.broadcast({
        #     "type": "sensor_update",
        #     "data": record_ack.status
        # })

        return SensorDataRecordedResponse(timestamp=db_reading.created_at, status="Success: Reading recorded")

    """
    Record multiple sensor readings in bulk.
    FOR DEVELOPMENT USE ONLY. WILL BE REMOVED IN PRODUCTION.
    """
    async def record_bulk_readings(self, db: AsyncSession, objs_in: list[SensorReadingCreate]) -> SensorDataRecordedResponse:
        sensor_height = (await self._get_sensor_config(db)).installation_height
        
        # Prepare DB objects
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = obj_in.model_dump()
            db_obj = SensorReading(**obj_in_data)
            db_obj.water_level_cm = sensor_height - db_obj.raw_distance_cm
            db_objs.append(db_obj)
        
        # Save to database
        await sensor_reading_crud.create_bulk_record(db, db_objs=db_objs)

        return SensorDataRecordedResponse(timestamp=datetime.now(timezone.utc), status="Success: Bulk Reading recorded")

sensor_reading_service = SensorReadingService()