from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class AdminAuditLogBase(BaseModel):
    action: str

class AdminAuditLogCreate(AdminAuditLogBase):
    admin_user_id: UUID

class AdminAuditLogResponse(AdminAuditLogBase):
    created_at: datetime
    admin_name: str

    class Config:
        from_attributes = True

class AdminAuditLogPaginatedResponse(BaseModel):
    logs: list[AdminAuditLogResponse]
    has_more: bool