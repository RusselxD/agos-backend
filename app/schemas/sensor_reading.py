from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

class SensorReadingBase(BaseModel):
    timestamp: datetime

class SensorReadingCreate(SensorReadingBase):
    sensor_id: int
    raw_distance_cm: float
    signal_strength: int | None = None  # RSSI in dBm (e.g., -40 to -85)
    signal_quality: str | None = None  # 'excellent', 'good', 'fair', 'poor'

class SensorReadingResponse(SensorReadingBase):
    id: int
    water_level_cm: float
    status: str
    change_rate: float | None # the first reading will have no change rate

    class Config:
        from_attributes = True

class SensorReadingPaginatedResponse(BaseModel):
    items: list[SensorReadingResponse]
    has_more: bool

    class Config:
        from_attributes = True

# For internal use in CRUD function sensor_reading.get_items_paginated
class SensorReadingMinimalResponse(BaseModel):
    id: int
    timestamp: datetime
    water_level_cm: float
    prev_water_level: float | None

# Response sent to the sensor device after recording a reading
class SensorDataRecordedResponse(BaseModel):
    timestamp: datetime
    status: str

# ================================================= #
# == Schemas for sensor reading summary endpoint == #
# ================================================= #
class WaterLevelSummary(BaseModel):
    current_cm: float
    change_rate: float
    trend: str  # 'rising', 'falling', 'stable'

class AlertSummary(BaseModel):
    level: str # 'normal', 'warning', 'critical'
    distance_to_warning_cm: float
    distance_to_critical_cm: float
    distance_from_critical_cm: float
    percentage_of_critical: float

class SensorReadingSummary(BaseModel):
    timestamp: datetime
    water_level: WaterLevelSummary
    alert: AlertSummary

class SensorReadingSummaryResponse(BaseModel):
    status: str # either "success" or "error"
    message: str # detailed message (for success, it's just "Retrieved successfully")
    sensor_reading: SensorReadingSummary | None = None