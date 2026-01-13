from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import SensorReadingPaginatedResponse, SensorReadingCreate, SensorDataRecordedResponse, SensorReadingForExportResponse
from app.core.database import get_db
from app.services import sensor_reading_service
from typing import List
from app.api.v1.dependencies import require_auth

router = APIRouter()

@router.get("/paginated", response_model=SensorReadingPaginatedResponse, dependencies=[Depends(require_auth)])
async def get_sensor_readings_paginated(page: int = 1, 
                                        page_size: int = 10,
                                        sensor_device_id: int = 1,
                                        db: AsyncSession = Depends(get_db)) -> SensorReadingPaginatedResponse:
    return await sensor_reading_service.get_items_paginated(db=db, page=page, page_size=page_size, sensor_device_id=sensor_device_id)

@router.post("/record", response_model=SensorDataRecordedResponse, status_code=201)
async def record_sensor_reading(reading: SensorReadingCreate, 
                                db: AsyncSession = Depends(get_db)) -> SensorDataRecordedResponse:
    return await sensor_reading_service.record_reading(db=db, obj_in=reading)

@router.get("/available-days", response_model=List[str], dependencies=[Depends(require_auth)])
async def get_available_reading_days(sensor_device_id: int = 1, db: AsyncSession = Depends(get_db)) -> list[str]:
    return await sensor_reading_service.get_avialable_reading_days(db=db, sensor_device_id=sensor_device_id)

@router.get("/for-export", response_model=SensorReadingForExportResponse, dependencies=[Depends(require_auth)])
async def get_sensor_readings_for_export(
    start_datetime: datetime,
    end_datetime: datetime,
    sensor_device_id: int = 1,
    db: AsyncSession = Depends(get_db)) -> SensorReadingForExportResponse:

    return await sensor_reading_service.get_readings_for_export(
        db=db, 
        start_datetime=start_datetime, 
        end_datetime=end_datetime,
        sensor_device_id=sensor_device_id
    )

# For DEV USE ONLY
@router.post("/bulk-record", response_model=SensorDataRecordedResponse, status_code=201)
async def bulk_record_sensor_readings(readings: List[SensorReadingCreate], 
                                    db: AsyncSession = Depends(get_db)) -> SensorDataRecordedResponse:
    return await sensor_reading_service.record_bulk_readings(db=db, objs_in=readings)