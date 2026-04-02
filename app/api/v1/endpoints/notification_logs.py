from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_auth
from app.core.database import get_db
from app.models.notification_template import NotificationType
from app.schemas.notification_log import DeliveryLogPaginatedResponse, ResponderNotificationSummary
from app.schemas.notification_analytics import NotificationAnalyticsResponse
from app.services.notification_log_service import notification_log_service

router = APIRouter(prefix="/notification-logs", tags=["notification-logs"])


@router.get("/responders-summary", dependencies=[Depends(require_auth)], response_model=list[ResponderNotificationSummary])
async def get_responders_summary(db: AsyncSession = Depends(get_db)) -> list[ResponderNotificationSummary]:
    return await notification_log_service.get_responders_summary(db=db)


@router.get("/responder/{responder_id}/deliveries", dependencies=[Depends(require_auth)], response_model=DeliveryLogPaginatedResponse)
async def get_responder_deliveries(
    responder_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    type: NotificationType | None = None,
    db: AsyncSession = Depends(get_db),
) -> DeliveryLogPaginatedResponse:
    return await notification_log_service.get_responder_deliveries(
        db=db,
        responder_id=responder_id,
        page=page,
        page_size=page_size,
        notification_type=type,
    )


@router.get("/analytics", dependencies=[Depends(require_auth)], response_model=NotificationAnalyticsResponse)
async def get_analytics(
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> NotificationAnalyticsResponse:
    return await notification_log_service.get_analytics(db=db, date_from=date_from, date_to=date_to)


@router.get("/export", dependencies=[Depends(require_auth)])
async def export_deliveries(
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(10000, ge=1, le=50000),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await notification_log_service.get_deliveries_for_export(db=db, date_from=date_from, date_to=date_to, limit=limit)
