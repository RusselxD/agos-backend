from app.api.v1.endpoints import auth
from app.api.v1.endpoints import system_settings
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"]) # tags is used for grouping in docs(swagger)
api_router.include_router(system_settings.router, prefix="/system-settings", tags=["system-settings"])