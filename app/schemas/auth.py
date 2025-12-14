from pydantic import BaseModel

class LoginRequest(BaseModel):
    phone_number: str
    password: str

# class LoginResponse(BaseModel):
#     access_token: str
#     token_type: str = "bearer"

# # You can add other auth-related schemas here later
# class PasswordResetRequest(BaseModel):
#     phone_number: str

# class PasswordResetConfirm(BaseModel):
#     phone_number: str
#     otp: str
#     new_password: str