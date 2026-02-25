import json
from datetime import datetime, timezone
from uuid import UUID

from pywebpush import webpush, WebPushException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import notification_delivery_crud, push_subscription_crud
from app.models.responder_related.notification_delivery import DeliveryStatus
from app.models.responder_related.push_subscription import PushSubscription

class NotificationService:
    
    async def send_notification_to_subscribers(
        self,
        notif_id: int,
        notif_title: str,
        notif_message: str,
        responder_ids: list[UUID],
        db: AsyncSession,
    ) -> None:
        # query subscriptions per responder_ids
        # iterate all subs, and call send_push
        # while iterating, also create NotificationDelivery records with status based on send_push result
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

        for subscription in subscriptions:
            is_sent = await self.send_push(
                subscription=subscription,
                notif_title=notif_title,
                notif_message=notif_message,
            )
            current = deliveries_by_responder.get(subscription.responder_id)

            if is_sent:
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

        await notification_delivery_crud.upsert_many_results(
            db=db,
            notification_id=notif_id,
            delivery_rows=list(deliveries_by_responder.values()),
        )



    async def send_push(self, subscription: PushSubscription, notif_title: str, notif_message: str) -> bool:
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
                    "title": notif_title,
                    "message": notif_message
                }),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIM_EMAIL}
            )
            return True
        except WebPushException as e:
            print(f"Push failed: {e}")
            return False

notification_service = NotificationService()
