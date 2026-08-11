from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import EvacuationEvent
from app.models.evacuation_event import EvacuationEventKind


class CRUDEvacuationEvent(CRUDBase[EvacuationEvent, None, None]):

    async def create_event(
        self,
        db: AsyncSession,
        *,
        location_id: int,
        kind: EvacuationEventKind,
        authorized_by: str,
        message: str,
        dispatch_id: int | None = None,
        basis_risk_score: int | None = None,
        basis_snapshot: dict | None = None,
    ) -> EvacuationEvent:
        event = EvacuationEvent(
            location_id=location_id,
            kind=kind,
            authorized_by=authorized_by,
            message=message,
            dispatch_id=dispatch_id,
            basis_risk_score=basis_risk_score,
            basis_snapshot=basis_snapshot,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    async def get_by_location(
        self, db: AsyncSession, location_id: int, limit: int = 100
    ) -> list[EvacuationEvent]:
        result = await db.execute(
            select(self.model)
            .where(self.model.location_id == location_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()


evacuation_event_crud = CRUDEvacuationEvent(EvacuationEvent)
