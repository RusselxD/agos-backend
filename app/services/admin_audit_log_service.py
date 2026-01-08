from app.models.admin_audit_log import AdminAuditLog
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import AdminAuditLogPaginatedResponse, AdminAuditLogResponse
from app.crud.admin_audit_log import admin_audit_logs as admin_audit_log_crud

class AdminAuditLogService:
    async def get_admin_logs_paginated(self, db: AsyncSession, page: int, page_size: int) -> AdminAuditLogPaginatedResponse:

        db_items: list[AdminAuditLog] = await admin_audit_log_crud.get_paginated(db=db, page=page, page_size=page_size)

        items = [
            AdminAuditLogResponse(
                id = log.id,
                action = log.action,
                created_at = log.created_at,
                first_name = log.admin_user.first_name,
                last_name = log.admin_user.last_name
            )
            for log in db_items
        ]

        has_more = len(db_items) > page_size
        return AdminAuditLogPaginatedResponse(
            items = items[:page_size],
            has_more = has_more
        )

admin_audit_log_service = AdminAuditLogService()