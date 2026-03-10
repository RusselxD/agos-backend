from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_auth
from app.core.database import get_db
from app.models.notification_template import NotificationType
from app.schemas.notification_log import DeliveryLogPaginatedResponse, ResponderNotificationSummary
from app.services.notification_log_service import notification_log_service

router = APIRouter(prefix="/notification-logs", tags=["notification-logs"])


@router.get("/responders-summary", dependencies=[Depends(require_auth)], response_model=list[ResponderNotificationSummary])
async def get_responders_summary(db: AsyncSession = Depends(get_db)) -> list[ResponderNotificationSummary]:
    return await notification_log_service.get_responders_summary(db=db)


@router.get("/responder/{responder_id}/deliveries", dependencies=[Depends(require_auth)], response_model=DeliveryLogPaginatedResponse)
async def get_responder_deliveries(
    responder_id: UUID,
    page: int = 1,
    page_size: int = 10,
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
