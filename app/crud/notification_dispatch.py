from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_dispatch import NotificationDispatch
from app.models.notification_template import NotificationType

from .base import CRUDBase


class CRUDNotificationDispatch(CRUDBase):

    async def create_for_send(
        self,
        db: AsyncSession,
        template_id: int | None,
        notif_type: NotificationType,
        title: str,
        message: str,
    ) -> NotificationDispatch:
        dispatch = NotificationDispatch(
            template_id=template_id,
            type=notif_type,
            title=title,
            message=message,
        )
        db.add(dispatch)
        await db.flush()
        return dispatch


notification_dispatch_crud = CRUDNotificationDispatch(NotificationDispatch)
