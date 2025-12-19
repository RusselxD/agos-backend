import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.schemas.admin_user import AdminUserCreate
from app.schemas.system_settings import SystemSettingsCreate
from app.crud.admin_user import admin_user as admin_user_crud
from app.crud.system_settings import system_settings as system_settings_crud

def seed_superuser(db: Session):
    test_user = AdminUserCreate(
        phone_number="+639207134335",
        first_name="Russel",
        last_name="Cabigquez",
        password="Russel-08",
        is_superuser=True
    )

    if not admin_user_crud.get_by_phone(db, phone_number=test_user.phone_number):
        admin_user_crud.create(db, obj_in=test_user)
        print("Seeded test admin user.")
    else:
        print("Test admin user already exists. Skipping seeding.")

def seed_settings(db: Session):
    
    settings_list = [
        SystemSettingsCreate(key="sensor_config", json_value={"installation_height": 200, "warning_threshold": 100, "critical_threshold": 150}),
        SystemSettingsCreate(key="data_retention_days", json_value=30),
    ]

    system_settings_crud.create_multi(db, objs_in=settings_list)
    print("Seeded system settings.")

def seed_db():
    db: Session = SessionLocal()

    seed_superuser(db)
    seed_settings(db)

    db.close()


if __name__ == "__main__":
    seed_db()