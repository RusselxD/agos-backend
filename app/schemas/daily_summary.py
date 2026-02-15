from pydantic import BaseModel
from datetime import date, datetime


class DailySummaryResponse(BaseModel):

    summary_date: date

    # Risk Score
    min_risk_score: int | None
    max_risk_score: int | None
    min_risk_timestamp: datetime | None
    max_risk_timestamp: datetime | None

    # Model Readings (Debris/Blockage)
    min_debris_count: int | None
    max_debris_count: int | None
    min_debris_timestamp: datetime | None
    max_debris_timestamp: datetime | None
    least_severe_blockage: str | None
    most_severe_blockage: str | None

    # Sensor Readings (Water Level)
    min_water_level_cm: float | None
    max_water_level_cm: float | None
    min_water_timestamp: datetime | None
    max_water_timestamp: datetime | None

    # Weather
    min_precipitation_mm: float | None
    max_precipitation_mm: float | None
    min_precip_timestamp: datetime | None
    max_precip_timestamp: datetime | None
    most_severe_weather_code: int | None

    class Config:
        from_attributes = True


class DailySummaryPaginatedResponse(BaseModel):
    items: list[DailySummaryResponse]
    has_more: bool

    class Config:
        from_attributes = True
