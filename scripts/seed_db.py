import sys
import asyncio
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import AdminUser, AdminAuditLog, SystemSettings, SensorDevice, CameraDevice, Location

async def seed_db():
    async with AsyncSessionLocal() as db:
        try:
            # --- Superuser ---
            result = await db.execute(select(AdminUser).where(AdminUser.phone_number == "+639207134335"))
            if not result.scalar_one_or_none():
                user = AdminUser(
                    phone_number="+639207134335",
                    first_name="Russel",
                    last_name="Cabigquez",
                    hashed_password=get_password_hash("Russel-08"),
                    is_superuser=True
                )
                db.add(user)
                await db.flush()
                
                db.add(AdminAuditLog(admin_user_id=user.id, action="Super Admin created by the system."))
                print("✅ Seeded superuser + audit log")
            
            # --- Settings ---
            settings = [
                SystemSettings(key="sensor_config", json_value={"installation_height": 200, "warning_threshold": 100, "critical_threshold": 150}),
                SystemSettings(key="alert_thresholds", json_value={"tier_1_max": 44, "tier_2_min": 45, "tier_2_max": 75, "tier_3_min": 76}),
                SystemSettings(key="data_retention_days", json_value=30),
                SystemSettings(key="auto_send_sms_when_critical", json_value=False),
            ]
            db.add_all(settings)
            print("✅ Seeded settings")

            # -- Location ---
            db.add(Location(name="Valenzuela Site 1", latitude=14.69, longitude=121.97))
            print("✅ Seeded location")
            
            # --- Sensor Device ---
            db.add(SensorDevice(device_name="WLS-RPI-001", location_id=1))
            print("✅ Seeded sensor device")

            # --- Camera Device ---
            db.add(CameraDevice(device_name="CAM-RPI-001", location_id=1))
            print("✅ Seeded camera device")

            await db.commit()
            print("\n🎉 Database seeding completed!")
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error seeding database: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(seed_db())