from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.responder_group import responder_group as responder_group_crud
from app.schemas import ResponderGroupItem


class ResponderGroupService:
    async def get_all_groups(self, db: AsyncSession) -> list[ResponderGroupItem]:
        groups = await responder_group_crud.get_all_with_member_ids(db=db)
        return [
            ResponderGroupItem(
                group_name=group.name,
                member_ids=[responder.id for responder in group.responders],
            )
            for group in groups
        ]


responder_group_service = ResponderGroupService()
