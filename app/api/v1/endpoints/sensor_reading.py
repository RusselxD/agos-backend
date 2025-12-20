from fastapi import APIRouter, Depends
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud
from sqlalchemy.orm import Session
from app.schemas.sensor_reading import SensorReadingPaginatedResponse
from app.core.database import get_db
from typing import Any

router = APIRouter()

@router.get("/", response_model=SensorReadingPaginatedResponse)
def get_sensor_readings_paginated(page: int = 1, page_size: int = 10, db: Session = Depends(get_db)) -> SensorReadingPaginatedResponse:
    paginated_response = sensor_reading_crud.get_items_paginated(db, page=page, page_size=page_size)
    return paginated_response