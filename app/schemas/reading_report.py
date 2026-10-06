from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import settings
from app.schemas.daily_summary import DailySummaryResponse


class ReadingReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    location_id: int = Field(gt=0)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_date < self.start_date:
            raise ValueError("Start date must be on or before end date")
        if (self.end_date - self.start_date).days + 1 > settings.REPORT_MAX_DAYS:
            raise ValueError(f"Reports support at most {settings.REPORT_MAX_DAYS} days")
        if self.end_date > datetime.now(settings.APP_TIMEZONE).date():
            raise ValueError("Reports cannot include future dates")
        return self


class ReadingReportResponse(BaseModel):
    id: UUID
    location_id: int
    location_name: str
    start_date: date
    end_date: date
    created_at: datetime
    expires_at: datetime
    timezone: str
    utc_offset_hours: float
    summaries: list[DailySummaryResponse]
    missing_dates: list[date]
    partial_dates: list[date] = Field(default_factory=list)
    status: Literal["pending", "streaming", "complete", "error"]
    analysis_text: str
    analysis_error: str | None
    analysis_completed_at: datetime | None
    analysis_model: str | None
    data_hash: str
    stats: dict
