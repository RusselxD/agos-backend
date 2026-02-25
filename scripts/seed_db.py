import sys
import asyncio
from pathlib import Path


sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.data_sources.sensor_device import SensorConfig
from app.models import AdminUser, AdminAuditLog, SystemSettings, SensorDevice, CameraDevice, Location, NotificationTemplate, NotificationType

async def seed_db():
    async with AsyncSessionLocal() as db:
        try:
            # --- Superuser ---
            result = await db.execute(select(AdminUser).where(AdminUser.phone_number == "+639207134335"))
            existing_user = result.scalar_one_or_none()
            if not existing_user:
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
            else:
                print("ℹ️ Superuser already exists, skipping")

            admin_user = existing_user if existing_user else user

            # --- Notification Templates ---
            notification_templates = [
                (NotificationType.WARNING, "Warning Alert", "A warning-level condition has been detected."),
                (NotificationType.CRITICAL, "Critical Alert", "A critical condition has been detected."),
                (NotificationType.BLOCKAGE, "Blockage Alert", "A blockage has been detected."),
            ]
            for ntype, title, message in notification_templates:
                existing = await db.execute(select(NotificationTemplate).where(NotificationTemplate.type == ntype))
                if existing.scalar_one_or_none():
                    print(f"ℹ️ Notification template '{ntype.value}' already exists, skipping")
                    continue
                db.add(NotificationTemplate(type=ntype, title=title, message=message, created_by_id=admin_user.id))
                print(f"✅ Seeded notification template '{ntype.value}'")

            # --- Settings ---
            settings = [
                {"key": "alert_thresholds", "json_value": {"tier_1_max": 44, "tier_2_min": 45, "tier_2_max": 75, "tier_3_min": 76}},
                {"key": "data_retention_days", "json_value": 30},
            ]
            for setting in settings:
                existing_setting = await db.execute(
                    select(SystemSettings).where(SystemSettings.key == setting["key"])
                )
                if existing_setting.scalar_one_or_none():
                    print(f"ℹ️ Setting '{setting['key']}' already exists, skipping")
                    continue

                db.add(SystemSettings(key=setting["key"], json_value=setting["json_value"]))
                print(f"✅ Seeded setting '{setting['key']}'")

            # -- Location ---
            location_name = "Valenzuela Site 1"
            location_result = await db.execute(select(Location).where(Location.name == location_name))
            location = location_result.scalar_one_or_none()
            if not location:
                location = Location(name=location_name, latitude=14.69, longitude=121.97)
                db.add(location)
                await db.flush()
                print("✅ Seeded location")
            else:
                print("ℹ️ Location already exists, skipping")
            
            # --- Sensor Device ---
            sensor_result = await db.execute(
                select(SensorDevice).where(SensorDevice.location_id == location.id)
            )
            if not sensor_result.scalar_one_or_none():
                db.add(SensorDevice(device_name="WLS-RPI-001", location_id=location.id, sensor_config=
                                    SensorConfig(installation_height=200, warning_threshold=100, critical_threshold=150)))
                print("✅ Seeded sensor device")
            else:
                print("ℹ️ Sensor device already exists, skipping")

            # --- Camera Device ---
            camera_result = await db.execute(
                select(CameraDevice).where(CameraDevice.location_id == location.id)
            )
            if not camera_result.scalar_one_or_none():
                db.add(CameraDevice(device_name="CAM-RPI-001", location_id=location.id))
                print("✅ Seeded camera device")
            else:
                print("ℹ️ Camera device already exists, skipping")

            await db.commit()
            print("\n🎉 Database seeding completed!")
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error seeding database: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(seed_db())
