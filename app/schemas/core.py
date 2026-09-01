from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.fusion_analysis import FusionAnalysisData


class LocationDetails(BaseModel):
    location_id: int
    location_name: str


class DeviceDetails(BaseModel):
    sensor_device_id: int
    sensor_device_name: str
    camera_device_id: int
    camera_device_name: str


class PublicStatusResponse(BaseModel):
    """Anonymous first-paint snapshot for the citizen PWA.

    ``level`` deliberately stops at ``high_risk``. An official ``evacuate``
    state comes only from the separately human-authorized ``public_alert``
    channel.
    """

    location_id: int
    level: Literal["safe", "alert", "high_risk", "unknown"]
    updated_at: datetime | None
    fusion_analysis: FusionAnalysisData | None
