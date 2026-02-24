from sqlalchemy import select

from fastapi import APIRouter, Depends
from app.core.config import settings
from app.models.responder_related.push_subscription import PushSubscription
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import SubscriptionSchema
from app.services import notification_service

router = APIRouter(
    prefix="/push",
    tags=["push"],
)

@router.get('/vapid-public-key')
def get_vapid_public_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe", status_code=204)
async def save_subscription(data: SubscriptionSchema, db: AsyncSession = Depends(get_db)) -> None:
    await notification_service.subscribe(data=data, db=db)
