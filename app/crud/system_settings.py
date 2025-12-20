from sqlalchemy.orm import Session
from app.models.system_settings import SystemSettings
from app.schemas.system_settings import SystemSettingsCreate, SystemSettingsUpdate
from app.crud.base import CRUDBase
from typing import Any

class CRUDSystemSettings(CRUDBase[SystemSettings, SystemSettingsCreate, SystemSettingsUpdate]):
    
    def get(self, db: Session, key: str) -> SystemSettings | None:
        return db.query(SystemSettings).filter(SystemSettings.key == key).first()
    
    def get_value(self, db: Session, key: str) -> Any:
        setting = self.get(db, key)
        if setting:
            return setting.json_value
        return None

system_settings = CRUDSystemSettings(SystemSettings)