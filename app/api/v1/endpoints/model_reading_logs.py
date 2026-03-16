from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_auth
from app.core.database import get_db
from app.schemas.model_reading_log import ModelReadingDetailResponse, ModelReadingPaginatedResponse
from app.services.model_reading_log_service import model_reading_log_service

router = APIRouter(prefix="/model-reading-logs", tags=["model-reading-logs"])


@router.get("/paginated", dependencies=[Depends(require_auth)], response_model=ModelReadingPaginatedResponse)
async def get_model_readings_paginated(
    page: int = 1,
    page_size: int = 10,
    camera_device_id: int = 1,
    blockage_status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> ModelReadingPaginatedResponse:
    return await model_reading_log_service.get_paginated(
        db=db,
        camera_device_id=camera_device_id,
        page=page,
        page_size=page_size,
        blockage_status=blockage_status,
    )


@router.get("/{reading_id}", dependencies=[Depends(require_auth)], response_model=ModelReadingDetailResponse)
async def get_model_reading_detail(
    reading_id: int,
    db: AsyncSession = Depends(get_db),
) -> ModelReadingDetailResponse:
    result = await model_reading_log_service.get_detail(db=db, reading_id=reading_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Model reading not found")
    return result
