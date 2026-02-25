from uuid import UUID

from pydantic import BaseModel

from .notification_template import NotificationTemplateResponse

class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str

class SubscriptionSchema(BaseModel):
    endpoint: str
    keys: SubscriptionKeys
    responder_id: UUID


class SendNotificationSchema(BaseModel):
    notif_template: NotificationTemplateResponse
    responder_ids: list[UUID]