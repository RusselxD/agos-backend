from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import EvacuationCenter
from app.schemas import EvacuationCenterCreate, EvacuationCenterUpdate


class CRUDEvacuationCenter(CRUDBase[EvacuationCenter, EvacuationCenterCreate, EvacuationCenterUpdate]):

    async def get_by_location(self, db: AsyncSession, location_id: int) -> list[EvacuationCenter]:
        result = await db.execute(
            select(self.model)
            .where(self.model.location_id == location_id)
            .order_by(self.model.name)
        )
        return result.scalars().all()


evacuation_center_crud = CRUDEvacuationCenter(EvacuationCenter)
