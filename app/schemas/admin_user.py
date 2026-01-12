from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

# --- BASE MODEL (Shared Fields) ---
class AdminUserBase(BaseModel):
    # These are the fields Super Users will input when creating a new admin.
    phone_number: str
    first_name: str
    last_name: str

class AdminUserCreate(AdminUserBase):
    created_by: UUID # ID of the superuser creating this admin
    password: str # Temporary password to be changed on first login.
class AdminUserLogin(BaseModel):
    phone_number: str
    password: str

class AdminChangePassword(BaseModel):
    current_password: str
    new_password: str

# Used in querying all admin users (Admins page)
class AdminUserResponse(AdminUserBase):
    # Inherits phone_number and name
    id: UUID
    is_superuser: bool
    is_enabled: bool
    last_login: datetime | None = None
    created_by: Optional[str] # Full name of the superuser who created this admin, None if seeded
    
    # Configuration to handle data from the SQLAlchemy ORM model
    class Config:
        from_attributes = True 