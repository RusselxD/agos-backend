from pydantic import BaseModel
from typing import Any

class SystemSettingsBase(BaseModel):
    key: str
    json_value: Any

class SystemSettingsCreate(SystemSettingsBase):
    pass

class SystemSettingsUpdate(SystemSettingsBase):
    pass

class SystemSettingsResponse(SystemSettingsBase):
    class Config:
        from_attributes = True