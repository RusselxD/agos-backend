from fastapi import APIRouter, Depends
from app.services import sensor_device_service
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import SensorDeviceStatusResponse
from app.core.database import get_db
from app.api.v1.dependencies import require_auth
from app.models import SensorConfig

router = APIRouter(prefix="/sensor-devices", tags=["sensor-devices"])


@router.get("/{id}/status", response_model=SensorDeviceStatusResponse, dependencies=[Depends(require_auth)])
async def get_sensor_device(id: int = 1, db: AsyncSession = Depends(get_db)) -> SensorDeviceStatusResponse:
    return await sensor_device_service.get_device_status(db=db, sensor_device_id=id)


@router.get("/{id}/config", response_model=SensorConfig, dependencies=[Depends(require_auth)])
async def get_sensor_device_config(id: int = 1, db: AsyncSession = Depends(get_db)) -> SensorConfig:
    return await sensor_device_service.get_device_config(db=db, sensor_device_id=id)