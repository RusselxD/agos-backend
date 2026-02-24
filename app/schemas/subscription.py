from uuid import UUID

from pydantic import BaseModel

class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str

class SubscriptionSchema(BaseModel):
    endpoint: str
    keys: SubscriptionKeys
    responder_id: UUID