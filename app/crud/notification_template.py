from uuid import UUID

from fastapi import HTTPException, status

from .base import CRUDBase
from app.models import NotificationTemplate
from app.models.notification_template import NotificationType
from app.schemas import CreateNotificationTemplateRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload


class CRUDNotificationTemplate(CRUDBase):

    async def get_all(self, db: AsyncSession) -> list[NotificationTemplate]:
        result = await db.execute(
            select(self.model)
            .options(joinedload(NotificationTemplate.creator))
            .execution_options(populate_existing=False)
        )
        return list(result.scalars().unique().all())


    async def create(
        self, db: AsyncSession, obj_in: CreateNotificationTemplateRequest, created_by_id: UUID
    ) -> NotificationTemplate:
        db_obj = NotificationTemplate(
            type=obj_in.type,
            title=obj_in.title,
            message=obj_in.message,
            created_by_id=created_by_id,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj, ["creator"])
        return db_obj


    async def get_by_type(
        self, db: AsyncSession, notification_type: NotificationType
    ) -> NotificationTemplate | None:
        result = await db.execute(
            select(NotificationTemplate)
            .where(NotificationTemplate.type == notification_type)
            .options(joinedload(NotificationTemplate.creator))
        )
        return result.scalar_one_or_none()


    async def demote_to_announcement(
        self, db: AsyncSession, template: NotificationTemplate
    ) -> None:
        template.type = NotificationType.ANNOUNCEMENT
        db.add(template)
        await db.commit()


    async def update(
        self, db: AsyncSession, template_id: int, obj_in: CreateNotificationTemplateRequest
    ) -> NotificationTemplate:
        template = await self.get(db, template_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification template not found")
        obj_data = obj_in.model_dump(exclude_unset=True)
        for field, value in obj_data.items():
            setattr(template, field, value)
        db.add(template)
        await db.commit()
        await db.refresh(template, ["creator"])
        return template

    async def delete(self, db: AsyncSession, template_id: int) -> str:
        """Delete template by id. Returns the template title for audit logging. Raises 404 if not found."""
        template = await self.get(db, template_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification template not found")
        title = template.title
        db.delete(template)
        await db.commit()
        return title


notification_template_crud = CRUDNotificationTemplate(NotificationTemplate)