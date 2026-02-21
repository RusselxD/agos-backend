from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from app.core.database import AsyncSessionLocal
from app.core.config import settings


scheduler = AsyncIOScheduler(timezone=settings.APP_TIMEZONE)


async def midnight_summary_job():
    """Generate daily summaries for the current day."""
    from app.services.daily_summary_service import daily_summary_service
    
    target_date = datetime.now(settings.APP_TIMEZONE).date()
    print(f"📅 Running daily summary job for {target_date}...")
    
    try:
        async with AsyncSessionLocal() as db:
            count = await daily_summary_service.generate_all_summaries(db, target_date)
            print(f"✅ Daily summaries generated: {count} summaries for {target_date}")
    except Exception as e:
        print(f"❌ Error generating daily summaries: {e}")


def start_scheduler():
    """Start the APScheduler with configured jobs."""
    scheduler.add_job(
        midnight_summary_job,
        CronTrigger(hour=0, minute=0, timezone=settings.APP_TIMEZONE),  # Run at midnight local time
        id="daily_summary_job",
        replace_existing=True,
        misfire_grace_time=3600  # Allow job to run up to 1 hour late if missed
    )
    scheduler.start()
    print(f"📅 Scheduler started - Daily summary job scheduled at configured cron time (UTC{settings.UTC_OFFSET_HOURS:+g})")


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("📅 Scheduler shutdown complete")
