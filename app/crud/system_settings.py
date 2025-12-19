from sqlalchemy.orm import Session
from app.models.system_settings import SystemSettings
from app.schemas.system_settings import SystemSettingsCreate, SystemSettingsUpdate
from app.crud.base import CRUDBase

class CRUDSystemSettings(CRUDBase[SystemSettings, SystemSettingsCreate, SystemSettingsUpdate]):
    
    def get(self, db: Session, key: str) -> SystemSettings | None:
        return db.query(SystemSettings).filter(SystemSettings.key == key).first()
    

system_settings = CRUDSystemSettings(SystemSettings)