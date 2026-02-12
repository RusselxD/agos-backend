from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas import LocationDetails, DeviceDetails
from app.api.v1.dependencies import require_auth
from app.services.core_service import core_service

router = APIRouter( prefix="/core", tags=["core"])


@router.get("/location-details", response_model=LocationDetails, dependencies=[Depends(require_auth)])
async def get_location_details(db: AsyncSession = Depends(get_db)) -> LocationDetails:
    return await core_service.get_default_location(db=db)


@router.get("/device-details", response_model=DeviceDetails, dependencies=[Depends(require_auth)])
async def get_device_details(db: AsyncSession = Depends(get_db), location_id: int = 1) -> DeviceDetails:
    return await core_service.get_device_details(db=db, location_id=location_id)