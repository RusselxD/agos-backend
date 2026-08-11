from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class EvacuationRecommendation(BaseModel):
    """backend → admin (WS). Fusion crossed the evacuation threshold; admin-facing
    only — NOT a public blast."""
    recommendation_id: str
    location_id: int
    risk_score: int
    alert_name: str
    triggered_conditions: list[str]
    suggested_message: str
    created_at: datetime


class EvacuationConfirmRequest(BaseModel):
    """admin → backend (REST). The human gate."""
    location_id: int
    kind: Literal["evacuate", "all_clear"] = "evacuate"
    message: str | None = None            # admin may override the suggested message
    recommendation_id: str | None = None  # for idempotency / dedupe


class PublicAlertPayload(BaseModel):
    """backend → citizen (WS + push + history back-fill)."""
    id: str | None = None  # stable id (== audit event id) for client-side dedupe
    level: Literal["be_alert", "evacuate", "all_clear"]
    title: str
    message: str
    location_id: int
    timestamp: datetime


class EvacuationEventResponse(BaseModel):
    id: UUID
    location_id: int
    dispatch_id: int | None
    kind: Literal["evacuate", "all_clear"]
    authorized_by: UUID
    basis_risk_score: int | None
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
