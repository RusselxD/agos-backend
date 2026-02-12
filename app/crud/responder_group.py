from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from app.crud.base import CRUDBase
from app.models import Group, Responders
from app.models.responder_related.responders import responder_groups


class CRUDResponderGroup(CRUDBase[Group, None, None]):
    async def get_by_name(self, db: AsyncSession, name: str) -> Group | None:
        result = await db.execute(
            select(self.model).where(self.model.name == name)
        )
        return result.scalars().first()

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

    async def ensure_exists(self, db: AsyncSession, name: str) -> Group:
        existing = await self.get_by_name(db=db, name=name)
        if existing:
            return existing

        group = self.model(name=name)
        db.add(group)

        # try except to avoid race condition on unique name
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing = await self.get_by_name(db=db, name=name)
            if existing:
                return existing
            raise
        await db.refresh(group)
        return group

    async def add_member_if_missing(self, db: AsyncSession, group_id: int, responder_id: UUID) -> None:
        exists_result = await db.execute(
            select(responder_groups.c.responder_id).where(
                responder_groups.c.group_id == group_id,
                responder_groups.c.responder_id == responder_id,
            )
        )
        if exists_result.first() is not None:
            return

        await db.execute(
            insert(responder_groups).values(
                responder_id=responder_id,
                group_id=group_id,
            )
        )


responder_group_crud = CRUDResponderGroup(Group)
