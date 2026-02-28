from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.dependencies import CurrentUser, require_auth
from app.core.database import get_db
from fastapi import Depends
from app.schemas import ResponderCreate, ResponderDetailsResponse, ResponderListItem
from app.services import responder_service

router = APIRouter(prefix="/responders", tags=["responders"])


@router.get("/all", dependencies=[Depends(require_auth)], response_model=list[ResponderListItem])
async def get_all_responders(db:AsyncSession = Depends(get_db)) -> list[ResponderListItem]:
    return await responder_service.get_all_responders(db=db)


@router.get("/additional-details/{responder_id}", dependencies=[Depends(require_auth)], response_model=ResponderDetailsResponse)
async def get_responder_details(responder_id: str, db:AsyncSession = Depends(get_db)) -> ResponderDetailsResponse:
    return await responder_service.get_responder_details(responder_id=responder_id, db=db)


@router.post("/bulk", response_model=list[ResponderListItem])
async def bulk_create_responders(
    responders: list[ResponderCreate], 
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_auth)) -> list[ResponderListItem]:
    
    return await responder_service.bulk_create_responders(responders=responders, db=db, user_id=user.id)
