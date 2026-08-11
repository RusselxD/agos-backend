from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, require_auth
from app.core.database import get_db
from app.schemas import EvacuationConfirmRequest, EvacuationEventResponse
from app.services import evacuation_service

router = APIRouter(prefix="/evacuation", tags=["evacuation"])


@router.post("/confirm", response_model=EvacuationEventResponse)
async def confirm_evacuation(
    payload: EvacuationConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> EvacuationEventResponse:
    """The human gate (admins only). Dispatches a public evacuate/all-clear alert
    to this location's citizen subscribers and writes an audit row."""
    return await evacuation_service.confirm(db=db, payload=payload, current_user=current_user)


@router.get("/events", response_model=list[EvacuationEventResponse])
async def get_evacuation_events(
    location_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_auth),
) -> list[EvacuationEventResponse]:
    return await evacuation_service.get_events(db=db, location_id=location_id)
