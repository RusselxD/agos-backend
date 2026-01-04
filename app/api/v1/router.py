from app.api.v1.endpoints import auth
from app.api.v1.endpoints import admin_users
from app.api.v1.endpoints import admin_audit_log
from app.api.v1.endpoints import system_settings
from app.api.v1.endpoints import sensor_reading
from app.api.v1.endpoints import sensor_device
from app.api.v1.endpoints import responder
# from app.api.v1.endpoints import weather_condition
from app.api.v1.endpoints import stream 
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"]) # tags is used for grouping in docs(swagger)
api_router.include_router(admin_users.router, prefix="/admin-users", tags=["admin-users"])
api_router.include_router(admin_audit_log.router, prefix="/admin-audit-logs", tags=["admin-audit-logs"])
api_router.include_router(system_settings.router, prefix="/system-settings", tags=["system-settings"])
api_router.include_router(sensor_reading.router, prefix="/sensor-readings", tags=["sensor-readings"])
api_router.include_router(sensor_device.router, prefix="/sensor-devices", tags=["sensor-devices"])
# api_router.include_router(weather_condition.router, prefix="/weather-condition", tags=["weather-condition"])
api_router.include_router(stream.router, prefix="/stream", tags=["stream"])
api_router.include_router(responder.router, prefix="/responder", tags=["responder"])