from app.models.admin_audit_log import AdminAuditLog
from app.schemas import AdminAuditLogCreate
from app.crud.base import CRUDBase
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.schemas import AdminAuditLogResponse

class CRUDAdminAuditLogs(CRUDBase[AdminAuditLog, AdminAuditLogCreate, None]):
    
    async def get_paginated(self, db, page: int = 1, page_size: int = 10) -> list[AdminAuditLogResponse]:
        skip = (page - 1) * page_size
        
        result = await db.execute(
            select(self.model)
            .options(joinedload(self.model.admin_user))  # Eager load the relationship
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(page_size + 1)
            .execution_options(populate_existing=False) # Disable tracking
        )
        return result.scalars().unique().all()

admin_audit_log_crud = CRUDAdminAuditLogs(AdminAuditLog)