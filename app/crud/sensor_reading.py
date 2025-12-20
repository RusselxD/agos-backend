from sqlalchemy.orm import Session
from app.models.sensor_readings import SensorReading
from app.schemas.sensor_reading import SensorReadingResponse, SensorReadingCreate, SensorReadingPaginatedResponse
from app.crud.base import CRUDBase
from app.crud.system_settings import system_settings as system_settings_crud
from app.models.sensor_devices import SensorDevice
from sqlalchemy import func, case

class CRUDSensorReading(CRUDBase[SensorReading, SensorReadingCreate, None]):
    
    def get_items_paginated(self, db: Session, page: int = 1, page_size: int = 10) -> SensorReadingPaginatedResponse:

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

        change_rate = (SensorReading.water_level_cm - prev_water_level).label('change_rate')

        skip = (page - 1) * page_size
        items = (
            db.query(
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
            .all()
        )
        has_more = len(items) > page_size
        return SensorReadingPaginatedResponse(items=items[:page_size], has_more=has_more)
    
    def create_multi(self, db: Session, objs_in: list[SensorReadingCreate]) -> list[SensorReadingResponse]:
        sensor_height = system_settings_crud.get_value(db, key="sensor_config")["installation_height"]
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = obj_in.model_dump()
            db_obj = SensorReading(**obj_in_data)
            db_obj.water_level_cm = sensor_height - db_obj.raw_distance_cm
            db_objs.append(db_obj)
        db.add_all(db_objs)
        db.commit()
        return db_objs
    
sensor_reading = CRUDSensorReading(SensorReading)