from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class ResponderOTPVerificationBase(BaseModel):
    phone_number: str

class ResponderOTPVerificationCreate(ResponderOTPVerificationBase):
    otp_hash: str
    expires_at: datetime

class ResponderOTPRequest(ResponderOTPVerificationBase):
    pass

class ResponderOTPVerifyRequest(ResponderOTPVerificationBase):
    otp: str

class ResponderOTPResponse(BaseModel):
    success: bool
    message: str

class ResponderOTPVerifyResponse(ResponderOTPResponse):
    send_again: bool

class ResponderBase(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    id_photo_path: str

class ResponderCreate(ResponderBase):
    pass

class ResponderListItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    phone_number: str
    status: str

class ResponderListResponse(BaseModel):
    responders: list[ResponderListItem]

class ResponderDetailsResponse(ResponderBase):
    id: UUID
    status: str
    created_at: datetime
    approved_by: str | None
    approved_at: datetime | None