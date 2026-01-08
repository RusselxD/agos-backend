from app.models.model_readings import ModelReadings
from app.schemas import ModelReadingCreate
from app.crud.base import CRUDBase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class CRUDModelReadings(CRUDBase[ModelReadings, ModelReadingCreate, None]):
    
    async def get_latest_reading(self, db: AsyncSession) -> ModelReadings | None:
        result = await db.execute(
            select(self.model.status, self.model.timestamp)
            .order_by(self.model.timestamp.desc())
            .limit(1)
        )
        return result.mappings().first()

model_readings = CRUDModelReadings(ModelReadings)