from app.models.data_sources.model_readings import ModelReadings
from app.schemas import ModelReadingCreate
from app.crud.base import CRUDBase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class CRUDModelReadings(CRUDBase[ModelReadings, ModelReadingCreate, None]):
    
    async def get_latest_reading(self, db: AsyncSession, camera_device_id: int) -> ModelReadings | None:
        result = await db.execute(
            select(self.model.blockage_status, self.model.timestamp)
            .filter(self.model.camera_device_id == camera_device_id)
            .order_by(self.model.timestamp.desc())
            .limit(1)
        )
        return result.mappings().first()

model_readings = CRUDModelReadings(ModelReadings)