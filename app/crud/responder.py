from app.crud.base import CRUDBase
from sqlalchemy import exists, select, update
from app.schemas.responder import ResponderOTPVerificationCreate
from app.models import RespondersOTPVerification as OTPModel
from app.models import Responder
from app.models.responder_related.responders import ResponderStatus
from sqlalchemy import delete
from datetime import datetime, timezone
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

class CRUDResponderOTPVerification(CRUDBase[ResponderOTPVerificationCreate, None, None]):

    async def get_by_responder_id(self, db: AsyncSession, responder_id: UUID) -> OTPModel | None:
        result = await db.execute(
            select(self.model)
            .filter(self.model.responder_id == responder_id)
            .execution_options(populate_existing=False)
        )
        return result.scalars().first()

    async def delete_by_responder_id(self, db: AsyncSession, responder_id: UUID, *, commit: bool = True) -> None:
        stmt = delete(self.model).where(self.model.responder_id == responder_id)
        await db.execute(stmt)
        if commit:
            await db.commit()

    async def increment_attempt_count(self, db: AsyncSession, record: OTPModel) -> None:
        record.attempt_count += 1
        db.add(record)
        await db.commit()

    async def upsert_otp(self, db: AsyncSession, obj_in: ResponderOTPVerificationCreate) -> None:
        """Delete existing OTP for responder and create new one"""
        stmt = delete(self.model).where(self.model.responder_id == obj_in.responder_id)
        await db.execute(stmt)
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()


class CRUDResponder(CRUDBase[None, None, None]):
    async def get_all(self, db: AsyncSession) -> list[Responder]:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.groups))
            .execution_options(populate_existing=False)
        )
        return result.scalars().unique().all()


    async def get_details(self, db : AsyncSession, id: str) -> Responder | None:
        result = await db.execute(
            select(self.model)
            .options(joinedload(self.model.admin_user)) # eager load
            .filter(self.model.id == id)
            .execution_options(populate_existing=False) # 
        )
        return result.scalars().first()


    async def approve_responder(self, db: AsyncSession, responder: Responder, user_id: str) -> None:
        responder.status = 'approved'
        responder.approved_at = datetime.now(timezone.utc)
        responder.approved_by = user_id
        db.add(responder)
        # commited at the service layer for idempotency


    # used in checking existing phone numbers
    async def record_exists(self, db: AsyncSession, phone_number: str) -> bool:
        result = await db.execute(
            select(exists().where(self.model.phone_number == phone_number))
        )
        return result.scalar()


    async def get_by_ids(self, db: AsyncSession, ids: list) -> list[Responder]:
        if not ids:
            return []
        result = await db.execute(
            select(self.model).where(self.model.id.in_(ids))
            .execution_options(populate_existing=False)
        )
        return list(result.scalars().unique().all())


    async def bulk_create_and_return(self, db: AsyncSession, objs_in: list, created_by_id: UUID) -> list[Responder]:
        # Build all objects in one pass
        db_objs = [
            self.model(**obj_in.model_dump(), created_by=created_by_id)
            for obj_in in objs_in
        ]
        db.add_all(db_objs)
        await db.flush()  # Flush to get IDs without committing
        
        # Collect IDs and fetch all in a single query with groups preloaded
        obj_ids = [obj.id for obj in db_objs]
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.groups))
            .where(self.model.id.in_(obj_ids))
        )
        await db.commit()
        return list(result.scalars().unique().all())


    async def activate(self, db: AsyncSession, responder_id: UUID, *, commit: bool = True) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == responder_id)
            .values(
                status=ResponderStatus.ACTIVE,
                activated_at=datetime.now(timezone.utc)
            )
        )
        await db.execute(stmt)
        if commit:
            await db.commit()


responder_otp_verification_crud = CRUDResponderOTPVerification(OTPModel)
responder_crud = CRUDResponder(Responder)
