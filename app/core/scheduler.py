from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
from app.core.config import settings


scheduler = AsyncIOScheduler(timezone=settings.APP_TIMEZONE)


async def midnight_summary_job():
    """Generate daily summaries for the current day."""
    from app.services import daily_summary_service
    
    target_date = datetime.now(settings.APP_TIMEZONE).date()
    print(f"📅 Running daily summary job for {target_date}...")
    
    try:
        async with AsyncSessionLocal() as db:
            count = await daily_summary_service.generate_all_summaries(db, target_date)
            print(f"✅ Daily summaries generated: {count} summaries for {target_date}")
    except Exception as e:
        print(f"❌ Error generating daily summaries: {e}")


async def data_cleanup_job():
    """Delete sensor readings, model readings, and weather data older than the configured retention period."""
    from app.crud.system_settings import system_settings_crud
    from app.crud.sensor_reading import sensor_reading_crud
    from app.crud.model_readings import model_readings_crud
    from app.crud.weather import weather_crud
    from app.crud.responder_otp_verification import responder_otp_verification_crud
    from app.crud.password_reset_otp import password_reset_otp_crud

    print("🗑️ Running data cleanup job...")

    try:
        async with AsyncSessionLocal() as db:
            now = datetime.now(settings.APP_TIMEZONE)

            # Data retention cleanup
            retention_days = await system_settings_crud.get_value(db, "data_retention_days")
            cutoff = now - timedelta(days=int(retention_days))

            sensor_count = await sensor_reading_crud.delete_older_than(db, cutoff)
            model_count = await model_readings_crud.delete_older_than(db, cutoff)
            weather_count = await weather_crud.delete_older_than(db, cutoff)

            # Expired OTP cleanup
            responder_otp_count = await responder_otp_verification_crud.delete_expired(db, now)
            password_otp_count = await password_reset_otp_crud.delete_expired(db, now)

            print(
                f"✅ Data cleanup complete (retention={retention_days}d): "
                f"sensor_readings={sensor_count}, model_readings={model_count}, weather={weather_count}, "
                f"expired_otps={responder_otp_count + password_otp_count}"
            )
    except Exception as e:
        print(f"❌ Error during data cleanup: {e}")


def start_scheduler():
    """Start the APScheduler with configured jobs."""
    scheduler.add_job(
        midnight_summary_job,
        CronTrigger(hour=0, minute=0, timezone=settings.APP_TIMEZONE),  # Run at midnight local time
        id="daily_summary_job",
        replace_existing=True,
        misfire_grace_time=3600  # Allow job to run up to 1 hour late if missed
    )
    scheduler.add_job(
        data_cleanup_job,
        CronTrigger(hour=1, minute=0, timezone=settings.APP_TIMEZONE),  # Run at 1:00 AM local time
        id="data_cleanup_job",
        replace_existing=True,
        misfire_grace_time=3600
    )
    scheduler.start()
    print(f"📅 Scheduler started - Daily summary job at midnight, data cleanup job at 1:00 AM (UTC{settings.UTC_OFFSET_HOURS:+g})")


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("📅 Scheduler shutdown complete")
