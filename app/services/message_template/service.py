"""Message template service: CRUD and audit."""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser
from app.crud import message_template_crud, admin_audit_log_crud
from app.schemas import AdminAuditLogCreate
from app.schemas.message_template import MessageTemplateCreate, MessageTemplateResponse

from .integrity_mapper import map_message_template_integrity_error


class MessageTemplateService:
    async def create_message_template(
        self,
        db: AsyncSession,
        template: MessageTemplateCreate,
        current_user: CurrentUser,
    ) -> MessageTemplateResponse:
        try:
            await message_template_crud.clear_auto_send_types(
                db=db,
                clear_warning=template.auto_send_on_warning,
                clear_critical=template.auto_send_on_critical,
                clear_blocked=template.auto_send_on_blocked,
            )

            message_template = await message_template_crud.create_no_commit(
                db=db,
                obj_in=template,
            )

            await admin_audit_log_crud.create_only_no_commit(
                db=db,
                obj_in=AdminAuditLogCreate(
                    admin_user_id=current_user.id,
                    action=f"Created message template '{message_template.template_name}'",
                ),
            )

            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            mapped = map_message_template_integrity_error(exc)
            if mapped:
                raise mapped
            raise
        except HTTPException:
            await db.rollback()
            raise
        except Exception:
            await db.rollback()
            raise

        return message_template

    async def update_message_template(
        self,
        db: AsyncSession,
        template_id: int,
        template: MessageTemplateCreate,
        current_user: CurrentUser,
    ) -> MessageTemplateResponse:
        try:
            existing_template = await message_template_crud.get_for_update(
                db=db,
                template_id=template_id,
            )
            if not existing_template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Message template not found.",
                )

            await message_template_crud.clear_auto_send_types(
                db=db,
                clear_warning=template.auto_send_on_warning,
                clear_critical=template.auto_send_on_critical,
                clear_blocked=template.auto_send_on_blocked,
                exclude_template_id=template_id,
            )

            previous_template_name = existing_template.template_name
            updated_template = await message_template_crud.update_no_commit(
                db=db,
                db_obj=existing_template,
                obj_in=template,
            )

            await admin_audit_log_crud.create_only_no_commit(
                db=db,
                obj_in=AdminAuditLogCreate(
                    admin_user_id=current_user.id,
                    action=f"Updated message template '{previous_template_name}'",
                ),
            )

            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            mapped = map_message_template_integrity_error(exc)
            if mapped:
                raise mapped
            raise
        except HTTPException:
            await db.rollback()
            raise
        except Exception:
            await db.rollback()
            raise

        return updated_template

    async def delete_message_template(
        self,
        db: AsyncSession,
        template_id: int,
        current_user: CurrentUser,
    ) -> None:
        try:
            existing_template = await message_template_crud.get_for_update(
                db=db,
                template_id=template_id,
            )
            if not existing_template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Message template not found.",
                )

            template_name = existing_template.template_name
            await message_template_crud.delete_no_commit(
                db=db,
                db_obj=existing_template,
            )

            await admin_audit_log_crud.create_only_no_commit(
                db=db,
                obj_in=AdminAuditLogCreate(
                    admin_user_id=current_user.id,
                    action=f"Deleted message template '{template_name}'",
                ),
            )

            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            mapped = map_message_template_integrity_error(exc)
            if mapped:
                raise mapped
            raise
        except HTTPException:
            await db.rollback()
            raise
        except Exception:
            await db.rollback()
            raise


message_template_service = MessageTemplateService()
