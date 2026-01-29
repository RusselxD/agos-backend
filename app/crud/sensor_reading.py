import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import SensorReading
from app.schemas import SensorReadingMinimalResponse, SensorReadingCreate, SensorReadingForExport
from app.crud.base import CRUDBase
from app.models import SensorDevice
from sqlalchemy import func, select, Row
from typing import List, Sequence
from sqlalchemy.orm import joinedload

class CRUDSensorReading(CRUDBase[SensorReading, SensorReadingCreate, None]):

    # For getting the latest reading for a specific sensor
    async def get_latest_reading(self, db: AsyncSession, sensor_device_id: int) -> SensorReading | None:
        result = await db.execute(
            select(self.model)
            .filter(self.model.sensor_device_id == sensor_device_id)
            .order_by(self.model.timestamp.desc())
            .limit(1)
            .execution_options(populate_existing=False) 
        )
        return result.scalars().first()

    # For getting the previous reading before a specific timestamp
    async def get_previous_reading(self, db: AsyncSession, before_timestamp: datetime) -> SensorReading | None:
        result = await db.execute(
            select(self.model)
            .filter(self.model.timestamp < before_timestamp)
            .order_by(self.model.timestamp.desc())
            .limit(1)
            .execution_options(populate_existing=False)
        )
        return result.scalars().first()

    # For "Sensor" page's table
    async def get_items_paginated(self, 
                                db: AsyncSession, 
                                sensor_device_id: int, 
                                page: int = 1, 
                                page_size: int = 10) -> List[SensorReadingMinimalResponse]:

        # Use LAG window function to get previous reading's water level
        prev_water_level = func.lag(self.model.water_level_cm).over(
            order_by=self.model.timestamp
        ).label("prev_water_level")

        skip = (page - 1) * page_size
        query = (
            select(
                self.model.id,
                self.model.timestamp, 
                self.model.water_level_cm,
                prev_water_level,
            )
            .filter(self.model.sensor_device_id == sensor_device_id)
            .order_by(self.model.timestamp.desc())
            .join(SensorDevice)
            .offset(skip)
            .limit(page_size + 1)
        )

        result = await db.execute(query)
        items = result.all()
        return items

    async def get_readings_since(self, db: AsyncSession, sensor_device_id: int, since_datetime: datetime) -> Sequence[Row]:
        result = await db.execute(
            select(self.model.water_level_cm, self.model.timestamp)
            .filter(self.model.sensor_device_id == sensor_device_id)
            .filter(self.model.timestamp >= since_datetime)
            .order_by(self.model.timestamp.asc())
        )
        return result.all()

    async def get_available_reading_days(self, db: AsyncSession, sensor_device_id: int) -> List[str]:
        result = await db.execute(
            select(func.distinct(func.date(self.model.timestamp)))
            .filter(self.model.sensor_device_id == sensor_device_id)
            .order_by(func.date(self.model.timestamp).desc())
        )
        dates = result.scalars().all()
        return [date.isoformat() for date in dates]

    async def get_readings_for_export(self, db: AsyncSession, start_datetime: datetime, end_datetime: datetime, sensor_device_id: int) -> list[SensorReading]:
        # Use LAG window function to get previous reading's water level
        prev_water_level = func.lag(self.model.water_level_cm).over(
            order_by=self.model.timestamp
        ).label("prev_water_level")
        
        result = await db.execute(
            select(
                self.model.timestamp,
                self.model.water_level_cm,
                prev_water_level,
                self.model.signal_strength,
            )
            .filter(self.model.sensor_device_id == sensor_device_id)
            .filter(self.model.timestamp >= start_datetime)
            .filter(self.model.timestamp <= end_datetime)
            .order_by(self.model.timestamp.desc())
        )
        return result.all()

    # For sensor's periodic reading insertion
    async def create_record(self, db: AsyncSession, db_obj: SensorReading) -> SensorReading:
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    # FOR DEVELOPMENT ONLY: Used by sensor simulator
    async def create_bulk_record(self, db: AsyncSession, db_objs: list[SensorReading]) -> None:
        db.add_all(db_objs)
        await db.commit()

sensor_reading = CRUDSensorReading(SensorReading)