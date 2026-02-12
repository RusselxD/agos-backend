# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.cron import CronTrigger
# from app.core.database import AsyncSessionLocal
# from app.crud import responder_otp_verification_crud

# class DatabaseCleanupService:
    
#     def __init__(self):
#         self.scheduler = AsyncIOScheduler()


#     async def start(self):
#         self.scheduler.add_job(
#             self._purge_expired_otps,
#             CronTrigger(minute="*/10"),  # Every 10 minutes
#             id="cleanup_expired_otps_job",
#         )
#         self.scheduler.start()
#         print("✅ Database cleanup service scheduler started.")

#     async def stop(self):
#         self.scheduler.shutdown()
#         print("✅ Database cleanup service scheduler stopped.")

#     async def _purge_expired_otps(self):
#         async with AsyncSessionLocal() as db:
#             try:
#                 count = await responder_otp_verification_crud.delete_expired_otps(db)
#                 print(f"✅ Purged {count} expired OTP records from the database.")
#             except Exception as e:
#                 print(f"❌ Error during OTP cleanup: {e}")


# database_cleanup_service = DatabaseCleanupService()