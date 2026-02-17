from app.api.v1.endpoints import auth, message_template
from app.api.v1.endpoints import admin_users
from app.api.v1.endpoints import admin_audit_log
from app.api.v1.endpoints import system_settings
from app.api.v1.endpoints import sensor_reading
from app.api.v1.endpoints import sensor_device
from app.api.v1.endpoints import responder
from app.api.v1.endpoints import stream 
from app.api.v1.endpoints import core
from app.api.v1.endpoints import weather
from app.api.v1.endpoints import responder_group
from app.api.v1.endpoints import daily_summary
from app.api.v1.endpoints import analysis
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_audit_log.router)
api_router.include_router(system_settings.router)
api_router.include_router(sensor_reading.router)
api_router.include_router(sensor_device.router)
api_router.include_router(core.router)
api_router.include_router(stream.router)
api_router.include_router(responder.router)
api_router.include_router(weather.router)
api_router.include_router(message_template.router)
api_router.include_router(responder_group.router)
api_router.include_router(daily_summary.router)
api_router.include_router(analysis.router)