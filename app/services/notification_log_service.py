from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.notification_log import notification_log_crud
from app.models.notification_template import NotificationType
from app.schemas.notification_log import (
    DeliveryLogItem,
    DeliveryLogPaginatedResponse,
    ResponderNotificationSummary,
)


class NotificationLogService:

    async def get_responders_summary(self, db: AsyncSession) -> list[ResponderNotificationSummary]:
        rows = await notification_log_crud.get_responders_with_notification_summary(db=db)
        return [
            ResponderNotificationSummary(
                id=row.Responder.id,
                first_name=row.Responder.first_name,
                last_name=row.Responder.last_name,
                phone_number=row.Responder.phone_number,
                status=row.Responder.status,
                total_notifications=row.total_notifications,
                total_sent=row.total_sent,
                total_failed=row.total_failed,
                total_pending=row.total_pending,
                total_acknowledged=row.total_acknowledged,
                last_notified_at=row.last_notified_at,
            )
            for row in rows
        ]


    async def get_responder_deliveries(
        self,
        db: AsyncSession,
        responder_id: UUID,
        page: int = 1,
        page_size: int = 10,
        notification_type: NotificationType | None = None,
    ) -> DeliveryLogPaginatedResponse:

        items, has_more = await notification_log_crud.get_deliveries_for_responder(
            db=db,
            responder_id=responder_id,
            page=page,
            page_size=page_size,
            notification_type=notification_type,
        )

        return DeliveryLogPaginatedResponse(
            items=[
                DeliveryLogItem(
                    id=d.id,
                    status=d.status,
                    sent_at=d.sent_at,
                    error_message=d.error_message,
                    created_at=d.created_at,
                    type=d.dispatch.type,
                    title=d.dispatch.title,
                    message=d.dispatch.message,
                    dispatched_at=d.dispatch.created_at,
                    is_acknowledged=d.acknowledgement is not None,
                    acknowledged_at=d.acknowledgement.acknowledged_at if d.acknowledgement else None,
                    acknowledge_message=d.acknowledgement.message if d.acknowledgement else None,
                )
                for d in items
            ],
            has_more=has_more,
        )


notification_log_service = NotificationLogService()
