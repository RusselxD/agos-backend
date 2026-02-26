import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from pywebpush import webpush, WebPushException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification_template import NotificationType
from app.crud import notification_delivery_crud, push_subscription_crud
from app.models.responder_related.notification_delivery import DeliveryStatus
from app.models.responder_related.push_subscription import PushSubscription


class PushResult:
    SENT = "sent"
    FAILED = "failed"
    GONE = "gone"  # 410 - subscription expired/unsubscribed, should be removed


class NotificationService:
    async def send_notification_to_subscribers(
        self,
        notif_id: int,
        notif_title: str,
        notif_message: str,
        notif_type: NotificationType,
        responder_ids: list[UUID],
        db: AsyncSession,
    ) -> None:
        
        if notif_type != NotificationType.ANNOUNCEMENT:
            raise HTTPException(
                status_code=400,
                detail="Manual notifications are only supported for announcements",
            )

        if not responder_ids:
            return

        subscriptions = await push_subscription_crud.get_by_responder_ids(
            responder_ids=responder_ids,
            db=db,
        )
        if not subscriptions:
            return

        deliveries_by_responder: dict[UUID, dict] = {}
        now = datetime.now(timezone.utc)
        subscriptions_to_remove: list[PushSubscription] = []

        for subscription in subscriptions:
            result = await self.send_push(
                subscription=subscription,
                notif_title=notif_title,
                notif_message=notif_message,
            )
            current = deliveries_by_responder.get(subscription.responder_id)

            if result == PushResult.GONE:
                subscriptions_to_remove.append(subscription)
            if result == PushResult.GONE and current and current["status"] == DeliveryStatus.SENT:
                continue
            if result == PushResult.GONE:
                deliveries_by_responder[subscription.responder_id] = {
                    "responder_id": subscription.responder_id,
                    "subscription_id": None,  # Sub is being deleted
                    "status": DeliveryStatus.FAILED,
                    "sent_at": None,
                    "error_message": "Push subscription expired or unsubscribed",
                }
                continue

            if result == PushResult.SENT:
                deliveries_by_responder[subscription.responder_id] = {
                    "responder_id": subscription.responder_id,
                    "subscription_id": subscription.id,
                    "status": DeliveryStatus.SENT,
                    "sent_at": now,
                    "error_message": None,
                }
                continue

            if current and current["status"] == DeliveryStatus.SENT:
                continue

            deliveries_by_responder[subscription.responder_id] = {
                "responder_id": subscription.responder_id,
                "subscription_id": subscription.id,
                "status": DeliveryStatus.FAILED,
                "sent_at": None,
                "error_message": "Push delivery failed",
            }

        for sub in subscriptions_to_remove:
            await db.delete(sub)
        if subscriptions_to_remove:
            await db.commit()

        await notification_delivery_crud.upsert_many_results(
            db=db,
            notification_id=notif_id,
            delivery_rows=list(deliveries_by_responder.values()),
        )


    async def send_push(
        self,
        subscription: PushSubscription,
        notif_title: str,
        notif_message: str,
    ) -> PushResult:
        
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=json.dumps({
                    "title": notif_title,
                    "message": notif_message,
                }),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIM_EMAIL},
            )
            return PushResult.SENT
        except WebPushException as e:
            status = getattr(getattr(e, "response", None), "status_code", None) or getattr(
                getattr(e, "response", None), "status", None
            )
            if status == 410: # subscription is no longer valid
                return PushResult.GONE
            return PushResult.FAILED

notification_service = NotificationService()
