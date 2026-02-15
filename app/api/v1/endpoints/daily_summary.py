from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.dependencies import require_auth
from app.schemas.daily_summary import DailySummaryPaginatedResponse
from app.core.database import get_db
from app.services import daily_summary_service

router = APIRouter(prefix="/daily-summaries", tags=["daily-summaries"])


@router.get("/paginated", response_model=DailySummaryPaginatedResponse, dependencies=[Depends(require_auth)])
async def get_daily_summaries_paginated(
    location_id: int,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db)
) -> DailySummaryPaginatedResponse:
    return await daily_summary_service.get_summaries_paginated(
        db=db, location_id=location_id, page=page, page_size=page_size
    )
