from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class ResponderSendSMSRequest(BaseModel):
    responder_ids: list[UUID]
    message: str

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

class ResponderBase(BaseModel):
    first_name: str
    last_name: str
    phone_number: str

class ResponderCreate(ResponderBase):
    pass

class ResponderForApproval(ResponderBase):
    status: str
    pass

from app.models.responder_related.responders import ResponderStatus


class ResponderListItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    phone_number: str
    status: ResponderStatus

    class Config:
        from_attributes = True

class ResponderDetailsResponse(BaseModel):
    created_at: datetime
    created_by: str
    activated_at: datetime | None

    class Config:
        from_attributes = True