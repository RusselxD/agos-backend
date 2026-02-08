from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from app.crud.base import CRUDBase
from app.models import Group, Responders


class CRUDResponderGroup(CRUDBase[Group, None, None]):
    async def get_all_with_member_ids(self, db: AsyncSession) -> list[Group]:
        result = await db.execute(
            select(self.model)
            .options(
                load_only(self.model.name),
                selectinload(self.model.responders).load_only(Responders.id),
            )
            .order_by(self.model.name)
            .execution_options(populate_existing=False)
        )
        return result.scalars().unique().all()


responder_group = CRUDResponderGroup(Group)
