from datetime import datetime
from app.crud.base import CRUDBase
from app.schemas import ResponderOTPVerificationCreate
from app.models import RespondersOTPVerification as OTPModel
from sqlalchemy import UUID, select, delete
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

    async def delete_expired(self, db: AsyncSession, now: datetime) -> int:
        result = await db.execute(
            delete(self.model).where(self.model.expires_at < now)
        )
        await db.commit()
        return result.rowcount

responder_otp_verification_crud = CRUDResponderOTPVerification(OTPModel)