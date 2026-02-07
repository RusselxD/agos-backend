from .base import CRUDBase
from app.models import MessageTemplate
from app.schemas import MessageTemplateCreate
from sqlalchemy import select, exists, update

class CRUDMessageTemplate(CRUDBase[MessageTemplate, MessageTemplateCreate, MessageTemplateCreate]):
    
    async def get_all(self, db) -> list[MessageTemplate]:
        result = await db.execute(
            select(self.model)
            .order_by(self.model.id)
        )
        return result.scalars().all()
    
    async def template_name_exists(self, db, name: str) -> bool:
        result = await db.execute(
            select(exists().where(self.model.template_name == name))
        )
        return result.scalar()
    
    async def get_by_template_name(self, db, name: str) -> MessageTemplate | None:
        result = await db.execute(
            select(self.model).where(self.model.template_name == name)
        )
        return result.scalars().first()

    async def clear_auto_send_on_critical(self, db, exclude_template_id: int | None = None) -> None:
        statement = (
            update(self.model)
            .where(self.model.auto_send_on_critical.is_(True))
            .values(auto_send_on_critical=False)
        )

        if exclude_template_id is not None:
            statement = statement.where(self.model.id != exclude_template_id)

        await db.execute(statement)
    
    async def update_by_id(self, db, template_id: int, obj_in: MessageTemplateCreate) -> MessageTemplate | None:
        message_template = await self.get(db=db, id=template_id)
        if not message_template:
            return None
        return await self.update(db=db, db_obj=message_template, obj_in=obj_in)

message_template = CRUDMessageTemplate(MessageTemplate)
