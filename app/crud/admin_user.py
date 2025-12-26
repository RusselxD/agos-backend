from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.admin_user import AdminUser
from app.schemas import AdminUserCreate, AdminUserUpdate, AdminUserResponse
from app.crud.base import CRUDBase
from app.core.security import get_password_hash
from sqlalchemy import select
from sqlalchemy.orm import joinedload

class CRUDAdminUser(CRUDBase[AdminUser, AdminUserCreate, AdminUserUpdate]):
    
    async def get_all_admins(self, db: AsyncSession) -> List[AdminUserResponse]:
        items: List[AdminUser] = await db.execute(
            select(self.model)
            .options(joinedload(self.model.admin_creator))
        )
        result = [
            AdminUserResponse(
                id=item.id,
                phone_number=item.phone_number,
                first_name=item.first_name,
                last_name=item.last_name,
                is_superuser=item.is_superuser,
                is_active=item.is_active,
                last_login=item.last_login,
                created_by=f"{item.admin_creator.first_name} {item.admin_creator.last_name}" if item.admin_creator else None
            ) for item in items.scalars().all()
        ]
        return result

    async def get_by_phone(self, db: AsyncSession, phone_number: str):
        result = await db.execute(
            select(AdminUser).filter(AdminUser.phone_number == phone_number)
        )
        return result.scalars().first()
    
    async def create(self, db: AsyncSession, obj_in: AdminUserCreate) -> AdminUser:
        db_obj = AdminUser(
            phone_number=obj_in.phone_number,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            hashed_password=get_password_hash(obj_in.password),
            is_superuser=obj_in.is_superuser
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

admin_user = CRUDAdminUser(AdminUser)   
