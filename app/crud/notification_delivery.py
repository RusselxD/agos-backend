from typing import Any
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.responder_related.acknowledgement import Acknowledgement
from app.models.responder_related.notification_delivery import DeliveryStatus, NotificationDelivery
from .base import CRUDBase


class CRUDNotificationDelivery(CRUDBase):

    async def upsert_many_results(self, db: AsyncSession, dispatch_id: int, delivery_rows: list[dict[str, Any]]) -> None:

        if not delivery_rows:
            return

        rows = [
            {
                "dispatch_id": dispatch_id,
                **row,
            }
            for row in delivery_rows
        ]

        stmt = insert(self.model).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_delivery_dispatch_responder",
            set_={
                "subscription_id": stmt.excluded.subscription_id,
                "status": stmt.excluded.status,
                "sent_at": stmt.excluded.sent_at,
                "error_message": stmt.excluded.error_message,
            },
        )
        await db.execute(stmt)
        await db.commit()


    async def get_alerts_per_responder(self, responder_id: UUID, db: AsyncSession) -> list[NotificationDelivery]:

        result = await db.execute(
            select(self.model)
            .options(
                joinedload(NotificationDelivery.dispatch),
                joinedload(NotificationDelivery.acknowledgement),
            )
            .where(NotificationDelivery.responder_id == responder_id)
            .order_by(NotificationDelivery.sent_at.desc())
        )
        return list(result.scalars().unique().all())


    async def get_unread_alerts_count(self, responder_id: UUID, db: AsyncSession) -> int:

        result = await db.execute(
            select(func.count(NotificationDelivery.id))
            .outerjoin(
                Acknowledgement,
                Acknowledgement.delivery_id == NotificationDelivery.id,
            )
            .where(
                NotificationDelivery.responder_id == responder_id,
                NotificationDelivery.status == DeliveryStatus.SENT,
                Acknowledgement.id.is_(None),
            )
        )
        return int(result.scalar_one())


notification_delivery_crud = CRUDNotificationDelivery(NotificationDelivery)
