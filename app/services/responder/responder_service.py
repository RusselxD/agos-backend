from app.models import Responder
from app.schemas import ResponderCreate, ResponderListItem, ResponderDetailsResponse
from fastapi import HTTPException
from app.crud.responder import responder_crud
from sqlalchemy.ext.asyncio import AsyncSession


class ResponderService:

    async def get_all_responders(self, db: AsyncSession) -> list[ResponderListItem]:
        responders = await responder_crud.get_all(db=db)
        ids_with_push = await responder_crud.get_responder_ids_with_push_subscription(db=db)
        return [
            ResponderListItem(
                id=r.id,
                first_name=r.first_name,
                last_name=r.last_name,
                phone_number=r.phone_number,
                status=r.status,
                has_push_subscription=r.id in ids_with_push,
            )
            for r in responders
        ]


    async def get_responder_details(self, responder_id: str, db: AsyncSession) -> ResponderDetailsResponse | None:
        responder: Responder = await responder_crud.get_details(db=db, id=responder_id)
        
        if not responder:
            raise HTTPException(status_code=404, detail="Responder not found.")
        
        return ResponderDetailsResponse(
            created_at=responder.created_at,
            created_by=f"{responder.admin_user.first_name} {responder.admin_user.last_name}",
            activated_at=responder.activated_at
        )


    async def bulk_create_responders(self, responders: list[ResponderCreate], db: AsyncSession, user_id: str) -> list[ResponderListItem]:
        created_responders = await responder_crud.bulk_create_and_return(db=db, objs_in=responders, created_by_id=user_id)
        return [
            ResponderListItem(
                id=responder.id,
                first_name=responder.first_name,
                last_name=responder.last_name,
                phone_number=responder.phone_number,
                status=responder.status,
                has_push_subscription=False,  # newly created responders have no subscriptions yet
            ) for responder in created_responders
        ]
    

responder_service = ResponderService()