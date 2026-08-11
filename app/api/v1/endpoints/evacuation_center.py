from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, require_auth
from app.core.database import get_db
from app.schemas import (
    EvacuationCenterCreate,
    EvacuationCenterResponse,
    EvacuationCenterUpdate,
)
from app.services import evacuation_center_service

router = APIRouter(prefix="/evacuation-centers", tags=["evacuation-centers"])


@router.get("", response_model=list[EvacuationCenterResponse])
async def list_centers(
    location_id: int, db: AsyncSession = Depends(get_db)
) -> list[EvacuationCenterResponse]:
    """Public: centers + live status for the citizen app and admin list."""
    return await evacuation_center_service.get_by_location(db=db, location_id=location_id)


@router.post("", response_model=EvacuationCenterResponse)
async def create_center(
    payload: EvacuationCenterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> EvacuationCenterResponse:
    return await evacuation_center_service.create_center(
        db=db, payload=payload, current_user=current_user
    )


@router.put("/{center_id}", response_model=EvacuationCenterResponse)
async def update_center(
    center_id: int,
    payload: EvacuationCenterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> EvacuationCenterResponse:
    return await evacuation_center_service.update_center(
        db=db, center_id=center_id, payload=payload, current_user=current_user
    )


@router.delete("/{center_id}", status_code=204)
async def delete_center(
    center_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> None:
    await evacuation_center_service.delete_center(
        db=db, center_id=center_id, current_user=current_user
    )
