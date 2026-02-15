from fastapi import APIRouter, Depends, HTTPException
from app.api.v1.dependencies import CurrentUser, require_auth
from app.schemas import SystemSettingsResponse, SystemSettingsUpdate
from app.crud import system_settings_crud
from app.services import system_settings_service
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter(prefix="/system-settings", tags=["system-settings"])


@router.get("/{key}", response_model=SystemSettingsResponse, dependencies=[Depends(require_auth)])
async def get_system_setting(key: str, db: AsyncSession = Depends(get_db)) -> SystemSettingsResponse:
    return await system_settings_crud.get(db=db, key=key)


@router.get("/{key}/value", response_model=None, dependencies=[Depends(require_auth)])
async def get_system_setting_value(key: str, db: AsyncSession = Depends(get_db)) -> any:
    return await system_settings_crud.get_value(db=db, key=key)


@router.put("/{key}", response_model=None)
async def update_system_setting(key: str, 
                                value: SystemSettingsUpdate, 
                                db: AsyncSession = Depends(get_db),
                                current_user: CurrentUser = Depends(require_auth)
                                ) -> any:
    return await system_settings_service.update_setting(
        db=db,
        key=key,
        value=value,
        current_user=current_user
    )