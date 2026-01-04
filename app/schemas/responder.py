from pydantic import BaseModel
from datetime import datetime

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