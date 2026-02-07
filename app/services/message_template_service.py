
from app.schemas.message_template import MessageTemplateCreate, MessageTemplateResponse
from app.api.v1.dependencies import CurrentUser
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.message_template import message_template as message_template_crud
from fastapi import HTTPException, status
from app.crud.admin_audit_log import admin_audit_log as admin_audit_log_crud
from app.schemas import AdminAuditLogCreate

class MessageTemplateService:
    
    async def create_message_template(self, db: AsyncSession, template: MessageTemplateCreate, current_user: CurrentUser) -> MessageTemplateResponse:

        message_template_exists = await message_template_crud.template_name_exists(db=db, name=template.template_name)

        if message_template_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template name already exists."
            )

        if template.auto_send_on_critical:
            await message_template_crud.clear_auto_send_on_critical(db=db)
        
        # Create the message template and get the created record
        message_template = await message_template_crud.create_and_return(db=db, obj_in=template)

        # Log the creation action
        await admin_audit_log_crud.create_only(
            db=db,
            obj_in=AdminAuditLogCreate(
                admin_user_id=current_user.id,
                action=f"Created message template '{message_template.template_name}'"
            )
        )

        return message_template
    
    async def update_message_template(self, db: AsyncSession, template_id: int, template: MessageTemplateCreate, current_user: CurrentUser) -> MessageTemplateResponse:
        existing_template = await message_template_crud.get(db=db, id=template_id)

        if not existing_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message template not found."
            )

        template_with_same_name = await message_template_crud.get_by_template_name(db=db, name=template.template_name)
        if template_with_same_name and template_with_same_name.id != template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template name already exists."
            )

        if template.auto_send_on_critical:
            await message_template_crud.clear_auto_send_on_critical(db=db, exclude_template_id=template_id)

        previous_template_name = existing_template.template_name
        updated_template = await message_template_crud.update_by_id(db=db, template_id=template_id, obj_in=template)

        if not updated_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message template not found."
            )

        await admin_audit_log_crud.create_only(
            db=db,
            obj_in=AdminAuditLogCreate(
                admin_user_id=current_user.id,
                action=f"Updated message template '{previous_template_name}'"
            )
        )

        return updated_template

message_template_service = MessageTemplateService()
