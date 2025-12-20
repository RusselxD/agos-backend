from fastapi import APIRouter, Depends
from app.crud.sensor_devices import sensor_device as sensor_device_crud
from sqlalchemy.orm import Session
from app.schemas.sensor_devices import SensorDeviceResponse
from app.core.database import get_db

router = APIRouter()

@router.get("/{id}/status", response_model=SensorDeviceResponse | None)
def get_sensor_device(id: int = 1, db: Session = Depends(get_db)) -> SensorDeviceResponse | None:
    sensor_device_details = sensor_device_crud.get(db, id=id)
    return sensor_device_details