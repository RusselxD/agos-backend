from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.location import DevicePerLocation
from app.services import cache_service
from app.api.v1.dependencies import require_auth

router = APIRouter()

@router.get("/location-id", response_model=int, dependencies=[Depends(require_auth)])
async def get_location_id(db: AsyncSession = Depends(get_db)) -> int:
    location_ids = await cache_service.get_all_location_ids(db=db)
    return location_ids[0]  # returns the first (default) location ID

@router.get("/device-ids", response_model=DevicePerLocation, dependencies=[Depends(require_auth)])
async def get_device_ids(db: AsyncSession = Depends(get_db), location_id: int = 1) -> DevicePerLocation:
    return await cache_service.get_device_ids_per_location(db=db, location_id=location_id)