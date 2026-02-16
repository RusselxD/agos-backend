from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.dependencies import require_auth
from app.schemas import DailySummaryResponse
from app.core.database import get_db
from app.services import daily_summary_service

router = APIRouter(prefix="/daily-summaries", tags=["daily-summaries"])

@router.get("", response_model=list[DailySummaryResponse], dependencies=[Depends(require_auth)])
async def get_daily_summaries(location_id: int, start_date: datetime, end_date: datetime, db: AsyncSession = Depends(get_db)) -> list[DailySummaryResponse]:
    return await daily_summary_service.get_daily_summaries(db=db, location_id=location_id, start_date=start_date, end_date=end_date)


@router.get("/available-days/{location_id}", response_model=list[datetime], dependencies=[Depends(require_auth)])
async def get_available_summary_days(location_id: int, db: AsyncSession = Depends(get_db)) -> list[datetime]:
    return await daily_summary_service.get_available_summary_days(db=db, location_id=location_id)
