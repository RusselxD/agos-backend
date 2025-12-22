import sys
import asyncio
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal

from app.crud.admin_user import admin_user as admin_user_crud
from app.crud.sensor_devices import sensor_device as sensor_device_crud
from app.crud.system_settings import system_settings as system_settings_crud
from app.crud.admin_audit_log import admin_audit_logs as admin_audit_logs_crud

from app.models.admin_user import AdminUser

from app.schemas.admin_user import AdminUserCreate
from app.schemas.admin_audit_log import AdminAuditLogCreate
from app.schemas.system_settings import SystemSettingsCreate
from app.schemas.sensor_devices import SensorDeviceCreate

async def seed_superuser(db):
    test_user = AdminUserCreate(
        phone_number="+639207134335",
        first_name="Russel",
        last_name="Cabigquez",
        password="Russel-08",
        is_superuser=True
    )

    existing_user = await admin_user_crud.get_by_phone(db, phone_number=test_user.phone_number)
    if existing_user:
        print("ℹ️  Test admin user already exists. Skipping seeding.")
        return
    
    new_user: AdminUser = await admin_user_crud.create(db, obj_in=test_user)
    await db.flush()  # Flush to get the ID before creating log
    print("✅ Seeded test admin user.")

    seeded_user_log = AdminAuditLogCreate(
        admin_user_id=new_user.id,
        action="Super Admin created by the system."
    )
    await admin_audit_logs_crud.create(db, obj_in=seeded_user_log)
    print("✅ Seeded admin audit log.")

async def seed_settings(db):
    settings_list = [
        SystemSettingsCreate(key="sensor_config", json_value={"installation_height": 200, "warning_threshold": 100, "critical_threshold": 150}),
        SystemSettingsCreate(key="data_retention_days", json_value=30),
    ]

    await system_settings_crud.create_multi(db, objs_in=settings_list)
    print("✅ Seeded system settings.")

async def seed_sensor_device(db):
    initial_sensor = SensorDeviceCreate(
        device_name="WLS-RPI-001",
        location="Creek 1"
    )

    await sensor_device_crud.create(db, obj_in=initial_sensor)
    print("✅ Seeded initial sensor device.")

async def seed_db():
    async with AsyncSessionLocal() as db:
        try:
            await seed_superuser(db)
            await seed_settings(db)
            await seed_sensor_device(db)
            await db.commit()
            print("\n🎉 Database seeding completed!")
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error seeding database: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(seed_db())