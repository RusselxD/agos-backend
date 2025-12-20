from fastapi import APIRouter, Depends
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.sensor_reading import SensorReadingPaginatedResponse, SensorReadingCreate, SensorDataRecordedResponse
from app.core.database import get_db

router = APIRouter()

@router.get("/paginated", response_model=SensorReadingPaginatedResponse)
async def get_sensor_readings_paginated(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db)) -> SensorReadingPaginatedResponse:
    paginated_response = await sensor_reading_crud.get_items_paginated(db, page=page, page_size=page_size)
    return paginated_response

@router.post("/record", response_model=SensorDataRecordedResponse, status_code=201)
async def record_sensor_reading(reading: SensorReadingCreate, db: AsyncSession = Depends(get_db)) -> SensorDataRecordedResponse:
    record_ack = await sensor_reading_crud.create_record(db, obj_in=reading)
    return record_ack