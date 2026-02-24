from sqlalchemy import select

from fastapi import APIRouter, Depends
from app.core.config import settings
from app.models.responder_related.push_subscription import PushSubscription
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import SubscriptionSchema

router = APIRouter(
    prefix="/push",
    tags=["push"],
)

@router.get('/vapid-public-key')
def get_vapid_public_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def save_subscription(
    data: SubscriptionSchema,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PushSubscription).filter_by(
            responder_id=data.responder_id,
            endpoint=data.endpoint
        )
    )
    existing = result.scalar_one_or_none()

    if not existing:
        sub = PushSubscription(
            responder_id=data.responder_id,
            endpoint=data.endpoint,
            p256dh=data.keys.p256dh,
            auth=data.keys.auth
        )
        db.add(sub)
        await db.commit()