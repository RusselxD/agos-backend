import uuid
from datetime import datetime

from sqlalchemy import delete, func, or_, select
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
        event_id: uuid.UUID | None = None,
        created_at: datetime | None = None,
    ) -> EvacuationEvent:
        # Allow the caller to pin id/created_at so the same identity can be shared
        # with the live public_alert WS payload (lets the citizen app dedupe the
        # live alert against the fetched history).
        fields: dict = dict(
            location_id=location_id,
            kind=kind,
            authorized_by=authorized_by,
            message=message,
            dispatch_id=dispatch_id,
            basis_risk_score=basis_risk_score,
            basis_snapshot=basis_snapshot,
        )
        if event_id is not None:
            fields["id"] = event_id
        if created_at is not None:
            fields["created_at"] = created_at
        event = EvacuationEvent(**fields)
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

    async def prune(
        self,
        db: AsyncSession,
        *,
        older_than: datetime,
        keep_per_location: int = 50,
    ) -> int:
        """Delete audit records that are older than `older_than` OR beyond the
        newest `keep_per_location` for their location.

        A row is kept only if it's within the age window AND still ranks in the
        recent N for its location.
        """
        ranked = select(
            self.model.id,
            self.model.created_at,
            func.row_number()
            .over(
                partition_by=self.model.location_id,
                order_by=self.model.created_at.desc(),
            )
            .label("rn"),
        ).subquery()

        stale_ids = select(ranked.c.id).where(
            or_(
                ranked.c.created_at < older_than,
                ranked.c.rn > keep_per_location,
            )
        )

        result = await db.execute(
            delete(self.model).where(self.model.id.in_(stale_ids))
        )
        await db.commit()
        return result.rowcount


evacuation_event_crud = CRUDEvacuationEvent(EvacuationEvent)
