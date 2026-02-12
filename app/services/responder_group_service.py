from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.dependencies import CurrentUser
from app.crud import responder_crud
from app.crud import responder_group_crud
from app.crud import admin_audit_log_crud
from app.models.responder_related.group import DEFAULT_ACTIVE_RESPONDERS_GROUP_NAME
from app.schemas import AdminAuditLogCreate
from app.schemas import ResponderGroupCreate, ResponderGroupItem


class ResponderGroupService:

    async def get_all_groups(self, db: AsyncSession) -> list[ResponderGroupItem]:
        await responder_group_crud.ensure_exists(
            db=db,
            name=DEFAULT_ACTIVE_RESPONDERS_GROUP_NAME,
        )
        groups = await responder_group_crud.get_all_with_member_ids(db=db)
        return [
            ResponderGroupItem(
                id=group.id,
                group_name=group.name,
                member_ids=[responder.id for responder in group.responders],
            )
            for group in groups
        ]


    async def create_group(self,db: AsyncSession, group: ResponderGroupCreate, current_user: CurrentUser) -> ResponderGroupItem:
        normalized_name = group.group_name.strip()
        if not normalized_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group name cannot be empty.",
            )
        group.group_name = normalized_name
        if normalized_name.casefold() == DEFAULT_ACTIVE_RESPONDERS_GROUP_NAME.casefold():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This group name is reserved for the system default active-responders group.",
            )


        if await responder_group_crud.name_exists(db=db, name=group.group_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A group with this name already exists.",
            )
        
        if group.member_ids:
            responders = await responder_crud.get_by_ids(db=db, ids=group.member_ids)
            if len(responders) != len(group.member_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more member IDs do not exist or are invalid.",
                )
        created = await responder_group_crud.create_with_members(
            db=db,
            name=group.group_name,
            member_ids=group.member_ids,
        )

        # Log
        await admin_audit_log_crud.create_only(
            db=db,
            obj_in=AdminAuditLogCreate(
                admin_user_id=current_user.id,
                action=f"Created responder group '{group.group_name}'"
            )
        )

        return ResponderGroupItem(
            id=created.id,
            group_name=created.name,
            member_ids=group.member_ids,
        )


responder_group_service = ResponderGroupService()
