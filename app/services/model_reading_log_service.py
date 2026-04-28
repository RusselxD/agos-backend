from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.model_readings import model_readings_crud
from app.schemas.model_reading_log import (
    ModelReadingDetailResponse,
    ModelReadingListItem,
    ModelReadingPaginatedResponse,
)


class ModelReadingLogService:

    async def get_paginated(
        self,
        db: AsyncSession,
        camera_device_id: int,
        page: int = 1,
        page_size: int = 10,
        blockage_status: str | None = None,
    ) -> ModelReadingPaginatedResponse:

        items, has_more = await model_readings_crud.get_items_paginated(
            db=db,
            camera_device_id=camera_device_id,
            page=page,
            page_size=page_size,
            blockage_status=blockage_status,
        )

        return ModelReadingPaginatedResponse(
            items=[
                ModelReadingListItem(
                    id=r.id,
                    blockage_status=r.blockage_status,
                    blockage_percentage=r.blockage_percentage,
                    timestamp=r.timestamp,
                )
                for r in items
            ],
            has_more=has_more,
        )

    async def get_detail(
        self,
        db: AsyncSession,
        reading_id: int,
    ) -> ModelReadingDetailResponse | None:

        reading = await model_readings_crud.get_by_id(db=db, reading_id=reading_id)
        if reading is None:
            return None

        return ModelReadingDetailResponse(
            id=reading.id,
            camera_device_id=reading.camera_device_id,
            image_path=reading.image_path,
            blockage_status=reading.blockage_status,
            blockage_percentage=reading.blockage_percentage,
            timestamp=reading.timestamp,
            created_at=reading.created_at,
        )


model_reading_log_service = ModelReadingLogService()
