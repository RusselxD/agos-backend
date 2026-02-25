from fastapi import APIRouter, Depends
from app.api.v1.dependencies import CurrentUser, require_auth
from app.schemas import NotificationTemplateResponse, CreateNotificationTemplateRequest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services import notification_template_service

router = APIRouter(
    prefix="/notification-templates",
    tags=["notification-templates"],
)


@router.get("/all", response_model=list[NotificationTemplateResponse], dependencies=[Depends(require_auth)])
async def get_all_notifications(db: AsyncSession = Depends(get_db)) -> list[NotificationTemplateResponse]:
    return await notification_template_service.get_all_notification_templates(db=db)


@router.post("/", response_model=NotificationTemplateResponse)
async def create_notification_template(
                                    payload: CreateNotificationTemplateRequest,
                                    db: AsyncSession = Depends(get_db),
                                    current_user: CurrentUser = Depends(require_auth)) -> NotificationTemplateResponse:

    return await notification_template_service.create_notification_template(
        payload=payload, db=db, created_by_id=current_user.id
    )


@router.put("/{template_id}", response_model=NotificationTemplateResponse)
async def update_notification_template(
                                    template_id: int,
                                    payload: CreateNotificationTemplateRequest,
                                    current_user: CurrentUser = Depends(require_auth),
                                    db: AsyncSession = Depends(get_db)) -> NotificationTemplateResponse:

    return await notification_template_service.update_notification_template(
        template_id=template_id,
        payload=payload,
        db=db,
        updated_by_id=current_user.id,
    )