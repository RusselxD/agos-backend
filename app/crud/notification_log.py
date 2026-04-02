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


    async def get_analytics(
        self,
        db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        from datetime import datetime, timezone

        # Base filters for sent deliveries
        base_filter = [NotificationDelivery.status == DeliveryStatus.SENT]
        if date_from:
            base_filter.append(NotificationDelivery.sent_at >= datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc))
        if date_to:
            base_filter.append(NotificationDelivery.sent_at <= datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc))

        # Overall stats
        stmt = (
            select(
                func.count(NotificationDelivery.id).label("total_sent"),
                func.count(Acknowledgement.id).label("total_acknowledged"),
                func.avg(
                    func.extract("epoch", Acknowledgement.acknowledged_at) -
                    func.extract("epoch", NotificationDelivery.sent_at)
                ).filter(Acknowledgement.id.isnot(None)).label("avg_response_seconds"),
            )
            .outerjoin(Acknowledgement, Acknowledgement.delivery_id == NotificationDelivery.id)
            .where(*base_filter)
        )
        result = await db.execute(stmt)
        overall = result.one()

        # Per-type breakdown
        type_stmt = (
            select(
                NotificationDispatch.type.label("notif_type"),
                func.count(NotificationDelivery.id).label("total"),
                func.count(Acknowledgement.id).label("acknowledged"),
                func.avg(
                    func.extract("epoch", Acknowledgement.acknowledged_at) -
                    func.extract("epoch", NotificationDelivery.sent_at)
                ).filter(Acknowledgement.id.isnot(None)).label("avg_response_seconds"),
            )
            .join(NotificationDispatch, NotificationDispatch.id == NotificationDelivery.dispatch_id)
            .outerjoin(Acknowledgement, Acknowledgement.delivery_id == NotificationDelivery.id)
            .where(*base_filter)
            .group_by(NotificationDispatch.type)
        )
        type_result = await db.execute(type_stmt)
        type_rows = type_result.all()

        # Top responders by response time
        top_stmt = (
            select(
                Responder.id,
                Responder.first_name,
                Responder.last_name,
                func.avg(
                    func.extract("epoch", Acknowledgement.acknowledged_at) -
                    func.extract("epoch", NotificationDelivery.sent_at)
                ).label("avg_response_seconds"),
                func.count(Acknowledgement.id).label("total_acknowledged"),
            )
            .join(NotificationDelivery, NotificationDelivery.responder_id == Responder.id)
            .join(Acknowledgement, Acknowledgement.delivery_id == NotificationDelivery.id)
            .where(*base_filter)
            .group_by(Responder.id)
            .order_by(func.avg(
                func.extract("epoch", Acknowledgement.acknowledged_at) -
                func.extract("epoch", NotificationDelivery.sent_at)
            ))
            .limit(10)
        )
        top_result = await db.execute(top_stmt)
        top_rows = top_result.all()

        return {
            "overall": overall,
            "type_rows": type_rows,
            "top_rows": top_rows,
        }

    async def get_deliveries_for_export(
        self,
        db: AsyncSession,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 10000,
    ) -> list[NotificationDelivery]:
        from datetime import datetime, timezone

        stmt = (
            select(NotificationDelivery)
            .options(
                joinedload(NotificationDelivery.dispatch),
                joinedload(NotificationDelivery.acknowledgement),
                joinedload(NotificationDelivery.responder),
            )
            .where(NotificationDelivery.status == DeliveryStatus.SENT)
        )

        if date_from:
            stmt = stmt.where(NotificationDelivery.sent_at >= datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc))
        if date_to:
            stmt = stmt.where(NotificationDelivery.sent_at <= datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc))

        stmt = stmt.order_by(NotificationDelivery.sent_at.desc()).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().unique().all())


notification_log_crud = CRUDNotificationLog()
