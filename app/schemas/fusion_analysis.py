from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class AnomalyType(str, Enum):
    OBSTRUCTED_SENSOR = "OBSTRUCTED_SENSOR"
    BLIND_CAMERA = "BLIND_CAMERA"
    STALE_SENSOR = "STALE_SENSOR"
    GHOST_FLOOD = "GHOST_FLOOD"
    CONFIDENCE_THRASHING = "CONFIDENCE_THRASHING"

class FusionData(BaseModel):
    alert_name: str
    combined_risk_score: int
    triggered_conditions: list[str]
    anomalies: list[AnomalyType] = []

class StatusBase(BaseModel):
    timestamp: datetime

class BlockageStatus(StatusBase):
    status: str

class WaterLevelStatus(StatusBase):
    water_level_cm: float
    change_rate: float
    critical_percentage: float
    trend: str  # e.g., "rising", "falling", "stable"

class WeatherStatus(StatusBase):
    precipitation_mm: float
    weather_condition: str

class FusionAnalysisData(BaseModel):
    fusion_data: FusionData
    blockage_status: BlockageStatus | None
    water_level_status: WaterLevelStatus | None
    weather_status: WeatherStatus | None


class IoTRiskScoreResponse(BaseModel):
    risk_score: int
