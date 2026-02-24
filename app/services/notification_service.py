from pywebpush import webpush, WebPushException
import json

from app.models.notification import Notification
from app.models.responder_related.push_subscription import PushSubscription
from app.core.config import settings

class NotificationService: 

    def send_push(self, subscription: PushSubscription, notification: Notification):
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
                    "title": notification.type.value,
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