from fastapi import APIRouter, Depends
from app.services import sensor_device_service
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.sensor_devices import SensorDeviceResponse
from app.core.database import get_db

router = APIRouter()

@router.get("/{id}/status", response_model=SensorDeviceResponse | None)
async def get_sensor_device(id: int = 1, db: AsyncSession = Depends(get_db)) -> SensorDeviceResponse | None:
    return await sensor_device_service.get_device_status(db, id=id)