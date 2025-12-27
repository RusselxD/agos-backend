from pydantic import BaseModel
from datetime import datetime

class FusionData(BaseModel):
    alert_name: str
    combined_risk_score: int
    triggered_conditions: list[str]

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
    blockage_status: BlockageStatus
    water_level_status: WaterLevelStatus
    weather_status: WeatherStatus