from uuid import UUID
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.responder_related.responders import Responder
from app.models.responder_related.notification_delivery import DeliveryStatus, NotificationDelivery
from app.models.responder_related.acknowledgement import Acknowledgement
from app.models.notification_dispatch import NotificationDispatch
from app.models.notification_template import NotificationType


class CRUDNotificationLog:

    async def get_responders_with_notification_summary(self, db: AsyncSession) -> list:
        delivery_subq = (
            select(
                NotificationDelivery.responder_id,
                func.count(NotificationDelivery.id).label("total_notifications"),
                func.count(case((NotificationDelivery.status == DeliveryStatus.SENT, 1))).label("total_sent"),
                func.count(case((NotificationDelivery.status == DeliveryStatus.FAILED, 1))).label("total_failed"),
                func.count(case((NotificationDelivery.status == DeliveryStatus.PENDING, 1))).label("total_pending"),
                func.max(NotificationDelivery.created_at).label("last_notified_at"),
            )
            .group_by(NotificationDelivery.responder_id)
            .subquery()
        )

        ack_subq = (
            select(
                Acknowledgement.responder_id,
                func.count(Acknowledgement.id).label("total_acknowledged"),
            )
            .group_by(Acknowledgement.responder_id)
            .subquery()
        )

        stmt = (
            select(
                Responder,
                func.coalesce(delivery_subq.c.total_notifications, 0).label("total_notifications"),
                func.coalesce(delivery_subq.c.total_sent, 0).label("total_sent"),
                func.coalesce(delivery_subq.c.total_failed, 0).label("total_failed"),
                func.coalesce(delivery_subq.c.total_pending, 0).label("total_pending"),
                func.coalesce(ack_subq.c.total_acknowledged, 0).label("total_acknowledged"),
                delivery_subq.c.last_notified_at,
            )
            .outerjoin(delivery_subq, Responder.id == delivery_subq.c.responder_id)
            .outerjoin(ack_subq, Responder.id == ack_subq.c.responder_id)
            .order_by(delivery_subq.c.last_notified_at.desc().nullslast())
        )

        result = await db.execute(stmt)
        return list(result.all())


    async def get_deliveries_for_responder(
        self,
        db: AsyncSession,
        responder_id: UUID,
        page: int = 1,
        page_size: int = 10,
        notification_type: NotificationType | None = None,
    ) -> tuple[list[NotificationDelivery], bool]:

        stmt = (
            select(NotificationDelivery)
            .options(
                joinedload(NotificationDelivery.dispatch),
                joinedload(NotificationDelivery.acknowledgement),
            )
            .where(NotificationDelivery.responder_id == responder_id)
        )

        if notification_type is not None:
            stmt = stmt.join(NotificationDispatch).where(NotificationDispatch.type == notification_type)

        stmt = stmt.order_by(NotificationDelivery.created_at.desc())

        # Fetch one extra to determine has_more
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size + 1)

        result = await db.execute(stmt)
        items = list(result.scalars().unique().all())

        has_more = len(items) > page_size
        if has_more:
            items = items[:page_size]

        return items, has_more


notification_log_crud = CRUDNotificationLog()
