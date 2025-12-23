from pydantic import BaseModel
from .reading_summary_response import ReadingSummaryResponse
from datetime import datetime

# =========================================================== #
# == Schemas for sensor reading summary websocket endpoint == #
# =========================================================== #
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

class SensorReadingSummaryResponse(ReadingSummaryResponse):
    sensor_reading: SensorReadingSummary | None = None