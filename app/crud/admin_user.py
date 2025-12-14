from sqlalchemy.orm import Session
from app.models.admin_user import AdminUser

class CRUDAdminUser:
    
    def get_by_number(self, db: Session, phone_number: str):
        return db.query(AdminUser).filter(AdminUser.phone_number == phone_number).first()
    


admin_user = CRUDAdminUser(AdminUser)