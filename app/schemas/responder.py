from typing import Literal

from app.models.notification_template import NotificationType
from app.models.responder_related.responders import ResponderStatus
from pydantic import BaseModel

NotifPreferenceKey = Literal["warning", "critical", "blockage", "announcement"]
from datetime import datetime
from uuid import UUID

class ResponderSendSMSRequest(BaseModel):
    responder_ids: list[UUID]
    message: str

class ResponderRegistrationRequest(BaseModel):
    phone_number: str

class ResponderOTPVerificationCreate(BaseModel):
    responder_id: UUID
    otp_hash: str
    expires_at: datetime

class ResponderOTPVerifyRequest(BaseModel):
    responder_id: UUID
    otp: str

class ResponderOTPVerifyResponse(BaseModel):
    success: bool
    message: str
    requires_resend: bool  # True = need to request new OTP, False = can retry current OTP
    responder_token: str | None = None

class ResponderBase(BaseModel):
    first_name: str
    last_name: str
    phone_number: str

class ResponderCreate(ResponderBase):
    pass

class ResponderForApproval(ResponderBase):
    responder_id: UUID
    status: ResponderStatus
    pass

class ResponderListItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    phone_number: str
    status: ResponderStatus
    has_push_subscription: bool = False

    class Config:
        from_attributes = True

class ResponderDetailsResponse(BaseModel):
    created_at: datetime
    created_by: str
    activated_at: datetime | None

    class Config:
        from_attributes = True


# For responders app
class ResponderDetails(BaseModel):
    id: str
    first_name: str
    last_name: str
    status: ResponderStatus
    phone_number: str
    location_id: int
    location_name: str
    created_at: datetime
    activated_at: datetime | None


class NotifPreferenceUpdateRequest(BaseModel):
    key: NotifPreferenceKey
    value: bool


class AlertListItem(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    message: str
    timestamp: datetime
    is_acknowledged: bool
    acknowledged_at: datetime | None
    acknowledge_message: str | None


class AlertPaginatedResponse(BaseModel):
    items: list[AlertListItem]
    has_more: bool


class AcknowledgeNotifRequest(BaseModel):
    delivery_id: UUID
    responder_id: UUID
    message: str | None = None


class AcknowledgeNotifResponse(BaseModel):
    acknowledged_at: datetime
    acknowledge_message: str | None = None