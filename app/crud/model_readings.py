from datetime import datetime
from app.models.data_sources.model_readings import ModelReadings
from app.schemas import ModelReadingCreate
from app.crud.base import CRUDBase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select


class CRUDModelReadings(CRUDBase[ModelReadings, ModelReadingCreate, None]):

    async def get_latest_reading(self, db: AsyncSession, camera_device_id: int) -> ModelReadings | None:

        result = await db.execute(
            select(self.model.blockage_status, self.model.timestamp)
            .filter(self.model.camera_device_id == camera_device_id)
            .order_by(self.model.timestamp.desc())
            .limit(1)
        )
        return result.mappings().first()

    async def get_items_paginated(
        self,
        db: AsyncSession,
        camera_device_id: int,
        page: int = 1,
        page_size: int = 10,
        blockage_status: str | None = None,
    ) -> tuple[list[ModelReadings], bool]:

        stmt = (
            select(self.model)
            .filter(self.model.camera_device_id == camera_device_id)
        )

        if blockage_status is not None:
            stmt = stmt.filter(self.model.blockage_status == blockage_status)

        stmt = stmt.order_by(self.model.timestamp.desc())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size + 1)

        result = await db.execute(stmt)
        items = list(result.scalars().all())

        has_more = len(items) > page_size
        if has_more:
            items = items[:page_size]

        return items, has_more

    async def get_by_id(self, db: AsyncSession, reading_id: int) -> ModelReadings | None:
        result = await db.execute(
            select(self.model).filter(self.model.id == reading_id)
        )
        return result.scalars().first()


    async def delete_older_than(self, db: AsyncSession, cutoff: datetime) -> int:
        result = await db.execute(
            delete(self.model).where(self.model.timestamp < cutoff)
        )
        await db.commit()
        return result.rowcount


model_readings_crud = CRUDModelReadings(ModelReadings)