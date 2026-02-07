from pydantic import BaseModel
from datetime import datetime

class SensorReadingBase(BaseModel):
    timestamp: datetime

class SensorReadingCreate(SensorReadingBase):
    sensor_device_id: int
    raw_distance_cm: float
    signal_strength: int  # RSSI in dBm (e.g., -40 to -85)

# Used in sensor reading table
class SensorReadingResponse(SensorReadingBase):
    id: int
    water_level_cm: float
    status: str
    change_rate: float | None # the first reading will have no change rate

    class Config:
        from_attributes = True

# Response model for exporting sensor readings to Excel/CSV
class SensorReadingForExport(SensorReadingBase):
    timestamp: str  # Override to use formatted string instead of datetime
    water_level_cm: float
    status: str
    change_rate: float | None
    signal_strength: int
    signal_quality: str

    class Config:
        from_attributes = True

# Response model for exporting sensor readings grouped by device
class SensorReadingForExportResponse(BaseModel):
    sensor_device_name: str
    readings: list[SensorReadingForExport]

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

    class Config:
        from_attributes = True

class SensorReadingTrendResponse(BaseModel):
    labels: list[str]
    levels: list[float]