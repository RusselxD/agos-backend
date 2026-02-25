from uuid import UUID

import json
from pywebpush import webpush, WebPushException

from app.models import NotificationTemplate
from app.models.notification_template import NotificationType
from app.models.responder_related.push_subscription import PushSubscription
from app.core.config import settings
from app.schemas import NotificationTemplateResponse, CreateNotificationTemplateRequest
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import notification_template_crud, admin_audit_log_crud
from app.schemas import AdminAuditLogCreate

class NotificationTemplateService: 

    async def get_all_notification_templates(self, db: AsyncSession) -> list[NotificationTemplateResponse]:
        notifs = await notification_template_crud.get_all(db=db)
        return [
            NotificationTemplateResponse(
                id=notif.id,
                type=notif.type,
                title=notif.title,
                message=notif.message,
            )    
            for notif in notifs        
        ]
    

    async def _demote_existing_if_conflicts(
        self, db: AsyncSession, incoming_type: NotificationType, exclude_template_id: int | None = None
    ) -> None:
        """If another template holds the incoming type, demote it to ANNOUNCEMENT to enforce uniqueness."""
        if incoming_type == NotificationType.ANNOUNCEMENT:
            return
        existing = await notification_template_crud.get_by_type(db=db, notification_type=incoming_type)
        if existing and (exclude_template_id is None or existing.id != exclude_template_id):
            await notification_template_crud.demote_to_announcement(db=db, template=existing)


    async def create_notification_template(
        self,
        payload: CreateNotificationTemplateRequest,
        db: AsyncSession,
        created_by_id: UUID,
    ) -> NotificationTemplateResponse:
        await self._demote_existing_if_conflicts(db, payload.type)
        template = await notification_template_crud.create(
            db=db, obj_in=payload, created_by_id=created_by_id
        )
        await admin_audit_log_crud.create_only(
            db=db,
            obj_in=AdminAuditLogCreate(
                admin_user_id=created_by_id,
                action=f"Created notification template '{template.title}'.",
            ),
        )
        return NotificationTemplateResponse(
            id=template.id,
            type=template.type,
            title=template.title,
            message=template.message
        )


    async def update_notification_template(
        self,
        template_id: int,
        payload: CreateNotificationTemplateRequest,
        db: AsyncSession,
        updated_by_id: UUID,
    ) -> NotificationTemplateResponse:
        await self._demote_existing_if_conflicts(db, payload.type, exclude_template_id=template_id)
        template = await notification_template_crud.update(
            db=db, template_id=template_id, obj_in=payload
        )
        await admin_audit_log_crud.create_only(
            db=db,
            obj_in=AdminAuditLogCreate(
                admin_user_id=updated_by_id,
                action=f"Updated notification template '{template.title}'.",
            ),
        )
        return NotificationTemplateResponse(
            id=template.id,
            type=template.type,
            title=template.title,
            message=template.message
        )


    async def send_push(self, subscription: PushSubscription, notification: NotificationTemplate) -> bool:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth
                    }
                },
                data=json.dumps({
                    "title": notification.title,
                    "message": notification.message
                }),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIM_EMAIL}
            )
            return True
        except WebPushException as e:
            print(f"Push failed: {e}")
            return False


notification_template_service = NotificationTemplateService()