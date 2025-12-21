from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sensor_readings import SensorReading
from app.schemas.sensor_reading import SensorReadingMinimalResponse, SensorReadingCreate
from app.crud.base import CRUDBase
from app.models.sensor_devices import SensorDevice
from sqlalchemy import func, select
from typing import List

class CRUDSensorReading(CRUDBase[SensorReading, SensorReadingCreate, None]):

    # For getting the latest reading for a specific sensor
    async def get_latest_reading(self, db: AsyncSession, sensor_id: int) -> SensorReading | None:
        result = await db.execute(
            select(SensorReading).filter(SensorReading.sensor_id == sensor_id).order_by(SensorReading.timestamp.desc())
        )
        return result.scalars().first()

    # For "Sensor" page's table
    async def get_items_paginated(self, db: AsyncSession, page: int = 1, page_size: int = 10) -> List[SensorReadingMinimalResponse]:

        # Use LAG window function to get previous reading's water level
        prev_water_level = func.lag(SensorReading.water_level_cm).over(
            order_by=SensorReading.timestamp
        ).label("prev_water_level")

        skip = (page - 1) * page_size
        query = (
            select(
                SensorReading.id,
                SensorReading.timestamp, 
                SensorReading.water_level_cm,
                prev_water_level,
            )
            .order_by(SensorReading.timestamp.desc())
            .join(SensorDevice)
            .offset(skip)
            .limit(page_size + 1)
        )

        result = await db.execute(query)
        items = result.all()
        return items

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