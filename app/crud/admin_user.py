from sqlalchemy.orm import Session
from app.models.admin_user import AdminUser
from app.schemas.admin_user import AdminUserCreate, AdminUserUpdate
from app.crud.base import CRUDBase
from app.core.security import get_password_hash

class CRUDAdminUser(CRUDBase[AdminUser, AdminUserCreate, AdminUserUpdate]):
    
    def get_by_phone(self, db: Session, phone_number: str):
        return db.query(AdminUser).filter(AdminUser.phone_number == phone_number).first()
    
    def create(self, db: Session, obj_in: AdminUserCreate) -> AdminUser:
        db_obj = AdminUser(
            phone_number=obj_in.phone_number,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            hashed_password=get_password_hash(obj_in.password),
            is_superuser=obj_in.is_superuser
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj   )
        return db_obj

admin_user = CRUDAdminUser(AdminUser)   
