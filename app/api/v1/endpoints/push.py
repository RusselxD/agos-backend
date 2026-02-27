from fastapi import APIRouter, Depends
from app.api.v1.dependencies import require_auth
from app.core.config import settings
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import SubscriptionSchema
from app.schemas.subscription import SendNotificationSchema
from app.services import push_subscription_service, notification_service

router = APIRouter(
    prefix="/push",
    tags=["push"],
)

@router.get('/vapid-public-key')
def get_vapid_public_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe", status_code=204)
async def save_subscription(data: SubscriptionSchema, db: AsyncSession = Depends(get_db)) -> None:
    await push_subscription_service.subscribe(data=data, db=db)


@router.post("/send-notification", status_code=204, dependencies=[Depends(require_auth)])
async def send_notification_to_responders(payload: SendNotificationSchema, db: AsyncSession = Depends(get_db)) -> None:
    await notification_service.send_notification_to_subscribers(
        payload=payload,
        db=db,
    )
