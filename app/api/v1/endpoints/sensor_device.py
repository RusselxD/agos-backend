from fastapi import APIRouter, Depends
from app.crud.sensor_devices import sensor_device as sensor_device_crud
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.sensor_devices import SensorDeviceResponse
from app.core.database import get_db

router = APIRouter()

@router.get("/{id}/status", response_model=SensorDeviceResponse | None)
async def get_sensor_device(id: int = 1, db: AsyncSession = Depends(get_db)) -> SensorDeviceResponse | None:
    sensor_device_details = await sensor_device_crud.get_device_status(db, id=id)
    return sensor_device_details