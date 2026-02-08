from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.dependencies import require_auth
from app.core.database import get_db
from app.schemas import ResponderGroupItem
from app.services import responder_group_service

router = APIRouter()

@router.get("/all", response_model=list[ResponderGroupItem], dependencies=[Depends(require_auth)])
async def get_all_groups(db: AsyncSession = Depends(get_db)) -> list[ResponderGroupItem]:
    return await responder_group_service.get_all_groups(db=db)
