from app.schemas.message_template import MessageTemplateCreate, MessageTemplateResponse
from app.api.v1.dependencies import CurrentUser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.crud import message_template_crud
from app.crud import admin_audit_log_crud
from app.schemas import AdminAuditLogCreate


class MessageTemplateService:
    @staticmethod
    def _map_integrity_error(exc: IntegrityError) -> HTTPException | None:
        error_text = str(exc.orig).lower()
        constraint_name = (
            getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            or getattr(exc.orig, "constraint_name", None)
            or ""
        ).lower()

        if (
            constraint_name == "message_templates_template_name_key"
            or constraint_name == "uq_message_templates_template_name"
            or "template_name" in error_text
        ):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template name already exists.",
            )

        if constraint_name == "uq_message_templates_auto_send_warning_true":
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only one template can have auto_send_on_warning enabled.",
            )

        if constraint_name == "uq_message_templates_auto_send_critical_true":
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only one template can have auto_send_on_critical enabled.",
            )

        if constraint_name == "uq_message_templates_auto_send_blocked_true":
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only one template can have auto_send_on_blocked enabled.",
            )

        # Fallback for environments where constraint name is not exposed.
        if (
            "auto_send_on_warning" in error_text
            or "auto_send_warning" in error_text
            or "warning_true" in error_text
        ):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only one template can have auto_send_on_warning enabled.",
            )

        if (
            "auto_send_on_critical" in error_text
            or "auto_send_critical" in error_text
            or "critical_true" in error_text
        ):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only one template can have auto_send_on_critical enabled.",
            )

        if (
            "auto_send_on_blocked" in error_text
            or "auto_send_blocked" in error_text
            or "blocked_true" in error_text
        ):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only one template can have auto_send_on_blocked enabled.",
            )

        return None

    async def create_message_template(self, db: AsyncSession, template: MessageTemplateCreate, current_user: CurrentUser) -> MessageTemplateResponse:
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
                    action=f"Created message template '{message_template.template_name}'"
                )
            )

            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            mapped_exception = self._map_integrity_error(exc)
            if mapped_exception:
                raise mapped_exception
            raise
        except HTTPException:
            await db.rollback()
            raise
        except Exception:
            await db.rollback()
            raise

        return message_template
    

    async def update_message_template(self, db: AsyncSession, template_id: int, template: MessageTemplateCreate, current_user: CurrentUser) -> MessageTemplateResponse:
        try:
            existing_template = await message_template_crud.get_for_update(
                db=db,
                template_id=template_id,
            )
            if not existing_template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Message template not found."
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
                    action=f"Updated message template '{previous_template_name}'"
                )
            )

            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            mapped_exception = self._map_integrity_error(exc)
            if mapped_exception:
                raise mapped_exception
            raise
        except HTTPException:
            await db.rollback()
            raise
        except Exception:
            await db.rollback()
            raise

        return updated_template


    async def delete_message_template(self, db: AsyncSession, template_id: int, current_user: CurrentUser) -> None:
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
            mapped_exception = self._map_integrity_error(exc)
            if mapped_exception:
                raise mapped_exception
            raise
        except HTTPException:
            await db.rollback()
            raise
        except Exception:
            await db.rollback()
            raise


message_template_service = MessageTemplateService()
