from app.api.v1.endpoints import auth
from app.api.v1.endpoints import system_settings
from app.api.v1.endpoints import sensor_reading
from app.api.v1.endpoints import sensor_device
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"]) # tags is used for grouping in docs(swagger)
api_router.include_router(system_settings.router, prefix="/system-settings", tags=["system-settings"])
api_router.include_router(sensor_reading.router, prefix="/sensor-readings", tags=["sensor-readings"])
api_router.include_router(sensor_device.router, prefix="/sensor-devices", tags=["sensor-devices"])