from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta
from app.core.database import AsyncSessionLocal


scheduler = AsyncIOScheduler()


async def midnight_summary_job():
    """Generate daily summaries for the previous day at midnight."""
    from app.services.daily_summary_service import daily_summary_service
    
    yesterday = date.today() - timedelta(days=1)
    print(f"📅 Running midnight summary job for {yesterday}...")
    
    try:
        async with AsyncSessionLocal() as db:
            count = await daily_summary_service.generate_all_summaries(db, yesterday)
            print(f"✅ Daily summaries generated: {count} summaries for {yesterday}")
    except Exception as e:
        print(f"❌ Error generating daily summaries: {e}")


def start_scheduler():
    """Start the APScheduler with configured jobs."""
    scheduler.add_job(
        midnight_summary_job,
        CronTrigger(hour=0, minute=0),  # Run at 00:00 daily
        id="daily_summary_job",
        replace_existing=True,
        misfire_grace_time=3600  # Allow job to run up to 1 hour late if missed
    )
    scheduler.start()
    print("📅 Scheduler started - Daily summary job scheduled for midnight (00:00)")


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("📅 Scheduler shutdown complete")
