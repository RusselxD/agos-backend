from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models import CitizenSubscription
from app.schemas import CitizenSubscriptionCreate


class CRUDCitizenSubscription(CRUDBase[CitizenSubscription, CitizenSubscriptionCreate, None]):

    async def upsert(self, db: AsyncSession, data: CitizenSubscriptionCreate) -> None:
        """Idempotent subscribe: re-subscribing the same device is a no-op update
        of the push keys (unique on location_id + endpoint)."""
        stmt = (
            pg_insert(self.model)
            .values(
                location_id=data.location_id,
                endpoint=data.endpoint,
                p256dh=data.keys.p256dh,
                auth=data.keys.auth,
            )
            .on_conflict_do_update(
                index_elements=["location_id", "endpoint"],
                set_={"p256dh": data.keys.p256dh, "auth": data.keys.auth},
            )
        )
        await db.execute(stmt)
        await db.commit()

    async def get_by_location(self, db: AsyncSession, location_id: int) -> list[CitizenSubscription]:
        result = await db.execute(
            select(self.model).where(self.model.location_id == location_id)
        )
        return result.scalars().all()

    async def delete_by_endpoint(
        self, db: AsyncSession, location_id: int, endpoint: str
    ) -> None:
        await db.execute(
            delete(self.model).where(
                self.model.location_id == location_id,
                self.model.endpoint == endpoint,
            )
        )
        await db.commit()

    async def delete_by_ids(self, db: AsyncSession, ids: list) -> None:
        """Prune dead subscriptions (push returned 410 Gone)."""
        if not ids:
            return
        await db.execute(delete(self.model).where(self.model.id.in_(ids)))
        await db.commit()


citizen_subscription_crud = CRUDCitizenSubscription(CitizenSubscription)
