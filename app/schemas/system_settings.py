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

class SensorConfigResponse(BaseModel):
    installation_height: float
    warning_threshold: float
    critical_threshold: float

    class Config:
        from_attributes = True

class AlertThresholdsResponse(BaseModel):
    tier_1_max: int
    tier_2_min: int
    tier_2_max: int
    tier_3_min: int

    class Config:
        from_attributes = True