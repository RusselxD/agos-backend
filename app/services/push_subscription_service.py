from app.crud import push_subscription_crud
from app.schemas import SubscriptionSchema
from sqlalchemy.ext.asyncio import AsyncSession


class PushSubscriptionService:
    
    async def subscribe(self, data: SubscriptionSchema, db: AsyncSession) -> None:
        existing = await push_subscription_crud.get_by_responder_id(
            responder_id=data.responder_id,
            endpoint=data.endpoint,
            db=db
        )

        if not existing: 
            await push_subscription_crud.create(data=data, db=db)


push_subscription_service = PushSubscriptionService()