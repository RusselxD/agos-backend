from uuid import UUID

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

    async def create_with_members(self, db: AsyncSession, name: str, member_ids: list[UUID]) -> Group:
        responders: list[Responders] = []
        if member_ids:
            result = await db.execute(
                select(Responders).where(Responders.id.in_(member_ids))
            )
            responders = list(result.scalars().unique().all())

        # Assign relationship while the instance is transient to avoid async lazy-load
        # of the previous collection state (MissingGreenlet).
        group = self.model(name=name, responders=responders)
        db.add(group)
        await db.commit()
        await db.refresh(group)
        return group

    async def name_exists(self, db: AsyncSession, name: str) -> bool:
        result = await db.execute(
            select(self.model).where(self.model.name == name)
        )
        return result.scalars().first() is not None


responder_group = CRUDResponderGroup(Group)
