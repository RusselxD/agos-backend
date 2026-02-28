from app.schemas.subscription import SubscriptionSchema
from .base import CRUDBase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.responder_related.push_subscription import PushSubscription
from uuid import UUID

class CRUDPushSubscription(CRUDBase):
    
    async def get_by_responder_id(self, responder_id: int, endpoint: str, db: AsyncSession) -> bool:

        result = await db.execute(
            select(self.model).filter_by(
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


    async def get_by_responder_ids(self, responder_ids: list[UUID], db: AsyncSession) -> list[PushSubscription]:
        
        if not responder_ids:
            return []

        result = await db.execute(
            select(self.model)
            .where(PushSubscription.responder_id.in_(responder_ids))
            .execution_options(populate_existing=False)
        )
        return list(result.scalars().all())

push_subscription_crud = CRUDPushSubscription(PushSubscription)
