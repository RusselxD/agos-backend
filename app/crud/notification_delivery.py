from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.responder_related.notification_delivery import NotificationDelivery

from .base import CRUDBase


class CRUDNotificationDelivery(CRUDBase):

    async def upsert_many_results(
        self,
        db: AsyncSession,
        notification_id: int,
        delivery_rows: list[dict[str, Any]],
    ) -> None:
        if not delivery_rows:
            return

        rows = [
            {
                "notification_id": notification_id,
                **row,
            }
            for row in delivery_rows
        ]

        stmt = insert(self.model).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_delivery_notification_responder",
            set_={
                "subscription_id": stmt.excluded.subscription_id,
                "status": stmt.excluded.status,
                "sent_at": stmt.excluded.sent_at,
                "error_message": stmt.excluded.error_message,
            },
        )
        await db.execute(stmt)
        await db.commit()


notification_delivery_crud = CRUDNotificationDelivery(NotificationDelivery)
