from fastapi import APIRouter, Depends
from app.schemas import MessageTemplateResponse, MessageTemplateCreate
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.dependencies import CurrentUser, require_auth
from app.core.database import get_db
from app.crud.message_template import message_template as message_template_crud
from app.services.message_template_service import message_template_service

router = APIRouter()

@router.get("/all", response_model=list[MessageTemplateResponse], dependencies=[Depends(require_auth)])
async def get_all_message_templates(db: AsyncSession = Depends(get_db)) -> list[MessageTemplateResponse]:
    return await message_template_crud.get_all(db=db)

@router.post("/", response_model=MessageTemplateResponse)
async def create_message_template(
                            template: MessageTemplateCreate, 
                            db: AsyncSession = Depends(get_db),
                            current_user: CurrentUser = Depends(require_auth)) -> MessageTemplateResponse:
    
    return await message_template_service.create_message_template(db=db, template=template, current_user=current_user)

@router.put("/{template_id}", response_model=MessageTemplateResponse)
async def update_message_template(
                            template_id: int, 
                            template: MessageTemplateCreate, 
                            db: AsyncSession = Depends(get_db),
                            current_user: CurrentUser = Depends(require_auth)) -> MessageTemplateResponse:
    
    return await message_template_service.update_message_template(db=db, template_id=template_id, template=template, current_user=current_user)