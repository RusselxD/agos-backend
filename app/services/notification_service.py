from pywebpush import webpush, WebPushException
import json

from app.models.notification import Notification
from app.models.responder_related.push_subscription import PushSubscription
from app.core.config import settings
from app.crud import push_subscription_crud
from app.schemas import SubscriptionSchema
from sqlalchemy.ext.asyncio import AsyncSession

class NotificationService: 

    async def subscribe(self, data: SubscriptionSchema, db: AsyncSession) -> None:
        existing = await push_subscription_crud.get_by_responder_id(
            responder_id=data.responder_id,
            endpoint=data.endpoint,
            db=db
        )

        if not existing: 
            await push_subscription_crud.create(data=data, db=db)


    async def send_push(self, subscription: PushSubscription, notification: Notification):
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


notification_service = NotificationService()