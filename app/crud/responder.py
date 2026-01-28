from app.crud.base import CRUDBase
from sqlalchemy import exists, select
from app.schemas import ResponderOTPVerificationCreate
from app.models.responders_otp_verification import RespondersOTPVerification as OTPModel
from app.models.responders import Responders
from sqlalchemy import delete
from datetime import datetime, timezone
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

class CRUDResponderOTPVerification(CRUDBase[ResponderOTPVerificationCreate, None, None]):
    
    async def record_exists(self, db: AsyncSession, phone_number: str) -> bool:
        result = await db.execute(
            select(exists().where(self.model.phone_number == phone_number))
        )
        return result.scalar()

    async def get_by_phone_number(self, db: AsyncSession, phone_number: str) -> OTPModel | None:
        result = await db.execute(
            select(self.model)
            .filter(self.model.phone_number == phone_number)
            .execution_options(populate_existing=False) # disable tracking
        )
        return result.scalars().first()

    async def save_incremented_attempt_count(self, db: AsyncSession, record: OTPModel) -> None:
        # already incremented in service layer
        db.add(record)
        await db.commit()

    async def delete(self, db: AsyncSession, obj: OTPModel) -> None:
        await db.delete(obj)
        await db.commit()

    async def delete_expired_otps(self, db: AsyncSession) -> int:
        now = datetime.now(timezone.utc)
        
        # DELETE FROM table WHERE expires_at < now
        stmt = delete(self.model).where(self.model.expires_at < now)
        result = await db.execute(stmt)
        
        await db.commit()
        return result.rowcount or 0 # Safely handle potential None values

class CRUDResponder(CRUDBase[None, None, None]):

    async def get_details(self, db : AsyncSession, id: str) -> Responders | None:
        result = await db.execute(
            select(self.model)
            .options(joinedload(self.model.admin_user)) # eager load
            .filter(self.model.id == id)
            .execution_options(populate_existing=False) # 
        )
        return result.scalars().first()

    async def approve_responder(self, db: AsyncSession, responder: Responders, user_id: str) -> None:
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

responder_otp_verification = CRUDResponderOTPVerification(OTPModel)
responder = CRUDResponder(Responders)