from http.client import HTTPException
from app.schemas import AdminUserCreate, AdminUserResponse, AdminAuditLogCreate
from app.crud.admin_user import admin_user as admin_user_crud
from app.crud.admin_audit_log import admin_audit_log as admin_audit_log_crud
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.admin_user import AdminUser
from app.api.v1.dependencies import CurrentUser
from app.utils import format_name_proper

class AdminUserService:
    
    async def get_all_admins(self, db: AsyncSession) -> list[AdminUserResponse]:
        admins: list[AdminUser] = await admin_user_crud.get_all_admins(db=db)
        result = [
            AdminUserResponse(
                id=item.id,
                phone_number=item.phone_number,
                first_name=item.first_name,
                last_name=item.last_name,
                is_superuser=item.is_superuser,
                is_enabled=item.is_enabled,
                last_login=item.last_login,
                created_by=f"{item.admin_creator.first_name} {item.admin_creator.last_name}" if item.admin_creator else None
            ) for item in admins
        ]
        return result

    async def create_new_admin_user(self, db: AsyncSession, admin_user_create: AdminUserCreate, current_user: CurrentUser) -> AdminUserResponse:

        # Check if phone number already exists
        if await admin_user_crud.phone_exists(db=db, phone_number=admin_user_create.phone_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is already registered."
            )
        
        # Set created_by to current superuser's ID
        admin_user_create.created_by = current_user.id

        # format names to proper case
        admin_user_create.first_name = format_name_proper(admin_user_create.first_name)
        admin_user_create.last_name = format_name_proper(admin_user_create.last_name)

        user_in_db = await admin_user_crud.create(db=db, obj_in=admin_user_create)

        # Log the creation action
        await admin_audit_log_crud.create_only(db=db, obj_in=AdminAuditLogCreate(
            admin_user_id=current_user.id,
            action=f"Added {user_in_db.first_name} {user_in_db.last_name} as a new admin."
        ))
    
        return AdminUserResponse(
            id=user_in_db.id,
            phone_number=user_in_db.phone_number,
            first_name=user_in_db.first_name,
            last_name=user_in_db.last_name,
            is_superuser=user_in_db.is_superuser,
            is_enabled=user_in_db.is_enabled,
            last_login=user_in_db.last_login,
            created_by=f"{user_in_db.admin_creator.first_name} {user_in_db.admin_creator.last_name}" if user_in_db.admin_creator else None
        )

admin_user_service = AdminUserService()