from fastapi import APIRouter, Depends
from app.services import weather_condition_service
from app.schemas.weather_condition import WeatherConditionResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter()

@router.get("/", response_model=WeatherConditionResponse)
async def get_weather_condition(sensor_id: int = 1, db: AsyncSession = Depends(get_db)) -> WeatherConditionResponse:
    return await weather_condition_service.get_weather_condition(db, sensor_id)
