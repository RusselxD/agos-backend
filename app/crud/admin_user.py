from sqlalchemy.ext.asyncio import AsyncSession
from app.models.admin_user import AdminUser
from app.schemas import AdminUserCreate
from app.crud.base import CRUDBase
from app.core.security import get_password_hash
from sqlalchemy import select, exists
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
from datetime import datetime

class CRUDAdminUser(CRUDBase[AdminUser, AdminUserCreate, None]):
    
    async def get_all_admins(self, db: AsyncSession) -> list[AdminUser]:
        items: list[AdminUser] = await db.execute(
            select(self.model)
            .options(joinedload(self.model.admin_creator))
            .execution_options(populate_existing=False)
        )
        return items.scalars().unique().all()

    async def get_by_phone(self, db: AsyncSession, phone_number: str) -> AdminUser | None:
        result = await db.execute(
            select(self.model)
            .filter(self.model.phone_number == phone_number)
            .execution_options(populate_existing=False)
        )
        return result.scalars().first()
    
    async def phone_exists(self, db: AsyncSession, phone_number: str) -> bool:
        result = await db.execute(
            select(exists().where(self.model.phone_number == phone_number))
        )
        return result.scalar()

    async def create(self, db: AsyncSession, obj_in: AdminUserCreate) -> AdminUser:
        db_obj = AdminUser(
            phone_number=obj_in.phone_number,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            hashed_password=get_password_hash(obj_in.password),
            created_by=obj_in.created_by
        )
        db.add(db_obj)
        await db.commit()
        
        # Re-query with eager loading to include admin_creator
        result = await db.execute(
            select(self.model)
            .options(joinedload(self.model.admin_creator))
            .filter(self.model.id == db_obj.id)
        )
        return result.scalars().first()

    async def update_password(self, db: AsyncSession, user_id: str, new_password: str) -> AdminUser:
        result = await db.execute(
            select(AdminUser).filter(AdminUser.id == user_id)
        )
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.hashed_password = get_password_hash(new_password)
        user.force_password_change = False

        await db.commit()
        await db.refresh(user)
        return user

    async def update_last_login(self, db: AsyncSession, user: AdminUser, last_login: datetime) -> None:
        user.last_login = last_login
        await db.commit()

admin_user_crud = CRUDAdminUser(AdminUser)   