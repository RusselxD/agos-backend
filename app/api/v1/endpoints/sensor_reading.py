from fastapi import APIRouter, Depends
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.sensor_reading import SensorReadingPaginatedResponse, SensorReadingCreate, SensorDataRecordedResponse
from app.core.database import get_db
from app.services.sensor_service import sensor_service
from typing import List

router = APIRouter()

@router.get("/paginated", response_model=SensorReadingPaginatedResponse)
async def get_sensor_readings_paginated(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db)) -> SensorReadingPaginatedResponse:
    paginated_response = await sensor_reading_crud.get_items_paginated(db, page=page, page_size=page_size)
    return paginated_response

@router.post("/record", response_model=SensorDataRecordedResponse, status_code=201)
async def record_sensor_reading(reading: SensorReadingCreate, db: AsyncSession = Depends(get_db)) -> SensorDataRecordedResponse:
    return await sensor_service.record_reading(db, obj_in=reading)

@router.post("/bulk-record", response_model=SensorDataRecordedResponse, status_code=201)
async def bulk_record_sensor_readings(readings: List[SensorReadingCreate], db: AsyncSession = Depends(get_db)) -> SensorDataRecordedResponse:
    return await sensor_reading_crud.create_bulk_record(db, objs_in=readings)