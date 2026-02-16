from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_
from app.models.data_sources.daily_summary import DailySummary
from app.crud.base import CRUDBase


class CRUDDailySummary(CRUDBase):
    
    async def get_by_location_and_date(self, db: AsyncSession, location_id: int, summary_date: date) -> DailySummary | None:
        result = await db.execute(
            select(self.model).where(
                and_(
                    DailySummary.location_id == location_id,
                    DailySummary.summary_date == summary_date
                )
            )
        )
        return result.scalar_one_or_none()


    async def get_summaries_by_location(self, db: AsyncSession, location_id: int, limit: int = 30) -> list[DailySummary]:
        """Get recent daily summaries for a location, ordered by date descending."""
        result = await db.execute(
            select(self.model)
            .where(DailySummary.location_id == location_id)
            .order_by(DailySummary.summary_date.desc())
            .limit(limit)
        )
        return result.scalars().all()


    async def get_summaries_in_range(self, db: AsyncSession, location_id: int, start_date: date, end_date: date) -> list[DailySummary]:
        """Get daily summaries for a location within a date range."""
        result = await db.execute(
            select(self.model).where(
                and_(
                    DailySummary.location_id == location_id,
                    DailySummary.summary_date >= start_date,
                    DailySummary.summary_date <= end_date
                )
            ).order_by(DailySummary.summary_date.asc())
        )
        return result.scalars().all()


    async def create_daily_summary(self, db: AsyncSession, location_id: int, summary_date: date, summary_data: dict) -> DailySummary:
        db_summary = self.model(
            location_id=location_id,
            summary_date=summary_date,
            **summary_data
        )
        db.add(db_summary)
        await db.commit()
        await db.refresh(db_summary)
        return db_summary


    async def get_daily_summaries(self, db: AsyncSession, location_id: int, start_date: datetime, end_date: datetime) -> list[DailySummary]:
        """Get daily summaries for a location within a datetime range."""
        result = await db.execute(
            select(self.model).where(
                and_(
                    DailySummary.location_id == location_id,
                    DailySummary.summary_date >= start_date,
                    DailySummary.summary_date <= end_date
                )
            ).order_by(DailySummary.summary_date.asc())
            .execution_options(populate_existing=False) # Disable tracking for better performance
        )
        return result.scalars().all()


    async def get_available_summary_days(self, db: AsyncSession, location_id: int) -> list[datetime]:
        """Get list of dates for which summaries are available for a location."""
        result = await db.execute(
            select(func.distinct(func.date(DailySummary.summary_date)))
            .filter(DailySummary.location_id == location_id)
            .order_by(func.date(DailySummary.summary_date).asc())
        )
        return result.scalars().all()


daily_summary_crud = CRUDDailySummary(DailySummary)
