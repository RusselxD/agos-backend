from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import AdminAuditLogPaginatedResponse
from app.core.database import get_db
from app.services import admin_audit_log_service

router = APIRouter()

@router.get("/paginated", response_model=AdminAuditLogPaginatedResponse)
async def get_admin_audit_logs_paginated(page: int = 1, 
                                        page_size: int = 10, 
                                        db: AsyncSession = Depends(get_db)) -> AdminAuditLogPaginatedResponse:

    return await admin_audit_log_service.get_admin_logs_paginated(db=db, page=page, page_size=page_size)