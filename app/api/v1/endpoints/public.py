from fastapi import APIRouter

from app.schemas import PublicStatusResponse
from app.services import core_service


router = APIRouter(prefix="/public", tags=["public"])


@router.get("/status", response_model=PublicStatusResponse)
async def get_public_status(location_id: int) -> PublicStatusResponse:
    """Latest citizen-safe status snapshot; live updates continue over WS."""
    return core_service.get_public_status(location_id=location_id)
