from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas import WeatherComprehensiveResponse
from app.services import weather_service
from app.api.v1.dependencies import require_auth

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/comprehensive-summary/{location_id}", response_model=WeatherComprehensiveResponse, dependencies=[Depends(require_auth)])
async def get_comprehensive_weather_summary(location_id: int = 1, db: AsyncSession = Depends(get_db)) -> WeatherComprehensiveResponse:
    return await weather_service.get_latest_comprehensive_weather_summary(db=db, location_id=location_id)