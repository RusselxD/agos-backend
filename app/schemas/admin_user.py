from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- BASE MODEL (Shared Fields) ---
class AdminUserBase(BaseModel):
    # These are the fields Super Users will input when creating a new admin.
    phone_number: str
    first_name: str
    last_name: str

class AdminUserCreate(AdminUserBase):
    is_superuser: Optional[bool] = False
    password: str 
    #Temporary password to be changed on first login.

class AdminUserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None

class AdminUserLogin(BaseModel):
    phone_number: str
    password: str

class AdminChangePassword(BaseModel):
    current_password: str
    new_password: str


# --- 3.1 PUBLIC RESPONSE (What the client sees) ---
class AdminUserResponse(AdminUserBase):
    # Inherits phone_number and name
    id: int
    is_superuser: bool
    is_active: bool
    
    # Configuration to handle data from the SQLAlchemy ORM model
    class Config:
        from_attributes = True 

# # --- 3.2 RESPONSE FOR NEW CREATION (Displays temporary password) ---
# class AdminUserNewCreation(AdminUserResponse):
#     # Used specifically after Phase 2, Step 3, to display the generated password.
#     temp_password: str

# # --- 3.3 RESPONSE FOR DEACTIVATION LOG ---
# class AdminDeactivationReason(BaseModel):
#     deactivation_reason: Optional[str] = None

# --- 4.1 DATABASE MODEL (Full representation of the user record) ---
class AdminUserInDB(AdminUserResponse):
    # Inherits all public fields from AdminUserResponse
    
    # Sensitive fields not shared with the client:
    hashed_password: str
    force_password_change: bool
    created_by: Optional[int] = None # ID of the admin who created this user
    
    # Deactivation audit trail fields:
    deactivated_at: Optional[datetime] = None
    deactivated_by: Optional[int] = None
    deactivation_reason: Optional[str] = None