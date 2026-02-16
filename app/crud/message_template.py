from .base import CRUDBase
from app.models import MessageTemplate
from app.schemas import MessageTemplateCreate
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDMessageTemplate(CRUDBase[MessageTemplate, MessageTemplateCreate, MessageTemplateCreate]):
    
    async def get_all(self, db: AsyncSession) -> list[MessageTemplate]:
        result = await db.execute(
            select(self.model)
            .order_by(self.model.id)
        )
        return result.scalars().all()
    

    async def clear_auto_send_types(
        self,
        db: AsyncSession,
        *,
        clear_warning: bool = False,
        clear_critical: bool = False,
        clear_blocked: bool = False,
        exclude_template_id: int | None = None,
    ) -> None:
        where_clauses = []
        values: dict[str, bool] = {}

        if clear_warning:
            where_clauses.append(self.model.auto_send_on_warning.is_(True))
            values["auto_send_on_warning"] = False
        if clear_critical:
            where_clauses.append(self.model.auto_send_on_critical.is_(True))
            values["auto_send_on_critical"] = False
        if clear_blocked:
            where_clauses.append(self.model.auto_send_on_blocked.is_(True))
            values["auto_send_on_blocked"] = False

        if not where_clauses:
            return

        statement = update(self.model).where(or_(*where_clauses)).values(**values)

        if exclude_template_id is not None:
            statement = statement.where(self.model.id != exclude_template_id)

        await db.execute(statement)


    async def get_for_update(self, db: AsyncSession, template_id: int) -> MessageTemplate | None:
        result = await db.execute(
            select(self.model)
            .where(self.model.id == template_id)
            .with_for_update()
        )
        return result.scalars().first()


    async def create_no_commit(self, db: AsyncSession, obj_in: MessageTemplateCreate) -> MessageTemplate:
        message_template = self.model(**obj_in.model_dump())
        db.add(message_template)
        await db.flush()
        return message_template


    async def update_no_commit(
        self,
        db: AsyncSession,
        db_obj: MessageTemplate,
        obj_in: MessageTemplateCreate,
    ) -> MessageTemplate:
        for field, value in obj_in.model_dump().items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        return db_obj


    async def delete_no_commit(self, db: AsyncSession, db_obj: MessageTemplate) -> None:
        await db.delete(db_obj)


message_template_crud = CRUDMessageTemplate(MessageTemplate)
