from app.schemas.subscription import SubscriptionSchema

from .base import CRUDBase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.responder_related.push_subscription import PushSubscription

class CRUDPushSubscription(CRUDBase):
    
    async def get_by_responder_id(self, responder_id: int, endpoint: str, db: AsyncSession) -> bool:
        result = await db.execute(
            select(PushSubscription).filter_by(
                responder_id=responder_id,
                endpoint=endpoint
            )
        )
        return result.scalar_one_or_none()


    async def create(self, data: SubscriptionSchema, db: AsyncSession) -> None:
        sub = PushSubscription(
            responder_id=data.responder_id,
            endpoint=data.endpoint,
            p256dh=data.keys.p256dh,
            auth=data.keys.auth
        )
        db.add(sub)
        await db.commit()

push_subscription_crud = CRUDPushSubscription(PushSubscription)
