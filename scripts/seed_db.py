import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.schemas.admin_user import AdminUserCreate
from app.crud.admin_user import admin_user as admin_user_crud

def seed_db():
    db: Session = SessionLocal()

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

    db.close()


if __name__ == "__main__":
    seed_db()