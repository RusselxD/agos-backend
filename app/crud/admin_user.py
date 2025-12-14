from sqlalchemy.orm import Session
from app.models.admin_user import AdminUser
from app.schemas.admin_user import AdminUserCreate, AdminUserUpdate
from app.crud.base import CRUDBase

class CRUDAdminUser(CRUDBase[AdminUser, AdminUserCreate, AdminUserUpdate]):
    
    def get_by_phone(self, db: Session, phone_number: str):
        return db.query(AdminUser).filter(AdminUser.phone_number == phone_number).first()
    


admin_user = CRUDAdminUser(AdminUser)