from pydantic import BaseModel

class LoginRequest(BaseModel):
    phone_number: str
    password: str

class ChangePasswordRequest(BaseModel):
    new_password: str