from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class AdminAuditLogBase(BaseModel):
    action: str

class AdminAuditLogCreate(AdminAuditLogBase):
    admin_user_id: UUID

class AdminAuditLogResponse(AdminAuditLogBase):
    id: int
    created_at: datetime
    first_name: str
    last_name: str

    class Config:
        from_attributes = True

class AdminAuditLogPaginatedResponse(BaseModel):
    items: list[AdminAuditLogResponse]
    has_more: bool