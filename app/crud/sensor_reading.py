from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sensor_readings import SensorReading
from app.schemas.sensor_reading import SensorReadingResponse, SensorReadingCreate, SensorReadingPaginatedResponse, SensorDataRecordedResponse
from app.schemas.system_settings import SensorConfigResponse
from app.crud.base import CRUDBase
from app.crud.sensor_devices import sensor_device as sensor_device_crud
from app.crud.system_settings import system_settings as system_settings_crud
from app.models.sensor_devices import SensorDevice
from sqlalchemy import func, case, select
from typing import Optional
from datetime import datetime, timedelta, timezone

class CRUDSensorReading(CRUDBase[SensorReading, SensorReadingCreate, None]):
    
    _sensor_config_cache: Optional[SensorConfigResponse] = None  # cached sensor configuration
    _cache_timestamp: Optional[datetime] = None                  # timestamp of when the cache was last updated
    _cache_ttl_timedelta = timedelta(minutes=60)                 # defines how long the cache is valid (Time To Live)

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

        # Use LAG window function to get previous reading's water level
        prev_water_level = func.lag(SensorReading.water_level_cm).over(
            order_by=SensorReading.timestamp
        )

        status = case(
            (prev_water_level == None, 'stable'),  # First reading
            (SensorReading.water_level_cm > prev_water_level + 1, 'rising'),
            (SensorReading.water_level_cm < prev_water_level - 1, 'falling'),
            else_='stable'
        ).label('status')

        # Calculate change rate, handling NULL for first reading
        change_rate = func.coalesce(SensorReading.water_level_cm - prev_water_level, 0).label('change_rate')

        skip = (page - 1) * page_size
        query = (
            select(
                SensorReading.id,
                SensorReading.timestamp, 
                SensorReading.water_level_cm,
                status,
                change_rate
            )
            .order_by(SensorReading.timestamp.desc())
            .join(SensorDevice)
            .offset(skip)
            .limit(page_size + 1)
        )

        result = await db.execute(query)
        items = result.all()

        has_more = len(items) > page_size
        return SensorReadingPaginatedResponse(items=items[:page_size], has_more=has_more)
    
    async def create_record(self, db: AsyncSession, obj_in: SensorReadingCreate) -> SensorDataRecordedResponse:
        obj_in_data = obj_in.model_dump() # Convert Pydantic model to dict

        if not await sensor_device_crud.get(db, id=obj_in.sensor_id):
            return SensorDataRecordedResponse(timestamp=datetime.now(timezone.utc), status="Error: Sensor device not found")

        # Get cached sensor installation height
        sensor_height = (await self._get_sensor_config(db)).installation_height
        
        # Create SensorReading DB object
        db_obj = SensorReading(**obj_in_data)
        db_obj.water_level_cm = sensor_height - db_obj.raw_distance_cm
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return SensorDataRecordedResponse(timestamp=db_obj.created_at, status="Success: Reading recorded")
        
    async def create_multi(self, db: AsyncSession, objs_in: list[SensorReadingCreate]) -> list[SensorReadingResponse]:
        sensor_height = (await self._get_sensor_config(db)).installation_height
        
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = obj_in.model_dump()
            db_obj = SensorReading(**obj_in_data)
            db_obj.water_level_cm = sensor_height - db_obj.raw_distance_cm
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        await db.commit()
        return db_objs
    
sensor_reading = CRUDSensorReading(SensorReading)