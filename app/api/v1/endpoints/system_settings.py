from fastapi import APIRouter, Depends, HTTPException
from app.schemas.system_settings import SystemSettingsResponse, SystemSettingsUpdate
from app.crud.system_settings import system_settings as system_settings_crud
from sqlalchemy.orm import Session
from app.core.database import get_db
from typing import Any

router = APIRouter()

@router.get("/{key}", response_model=SystemSettingsResponse)
def get_system_setting(key: str, db: Session = Depends(get_db)) -> SystemSettingsResponse:
    settings = system_settings_crud.get(db, key=key)
    if not settings:
        raise HTTPException(status_code=404, detail="System settings not found")
    return settings

@router.get("/{key}/value", response_model=Any)
def get_system_setting_value(key: str, db: Session = Depends(get_db)) -> Any:
    json_value = system_settings_crud.get_value(db, key)
    if not json_value:
        raise HTTPException(status_code=404, detail="System settings not found")
    return json_value

@router.put("/{key}", response_model=Any)
def update_system_setting(key: str, value: SystemSettingsUpdate, db: Session = Depends(get_db)) -> Any:
    settings = system_settings_crud.get(db, key=key)
    if not settings:
        raise HTTPException(status_code=404, detail="System settings not found")
    updated_settings = system_settings_crud.update(db, db_obj=settings, obj_in=value)
    return updated_settings.json_value