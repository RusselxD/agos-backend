from datetime import datetime
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.password_reset_otp import PasswordResetOTP
from app.crud.base import CRUDBase


class CRUDPasswordResetOTP(CRUDBase):

    async def delete_expired(self, db: AsyncSession, now: datetime) -> int:
        result = await db.execute(
            delete(self.model).where(self.model.expires_at < now)
        )
        await db.commit()
        return result.rowcount


password_reset_otp_crud = CRUDPasswordResetOTP(PasswordResetOTP)
