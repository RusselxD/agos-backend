from datetime import datetime
from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from .base import CRUDBase
from app.models import RefreshToken
from sqlalchemy.orm import selectinload

class CRUDRefreshToken(CRUDBase[None, None, None]):
    
    async def get_by_token(self, db: AsyncSession, token: str) -> RefreshToken:
        result = await db.execute(
            select(RefreshToken).
            where(RefreshToken.token == token)
            .options(selectinload(RefreshToken.admin_user))
        )
        return result.scalar_one_or_none()


    async def create(self, user_id: UUID, token: str, expires_at: datetime, db: AsyncSession) -> None:
        db_token = RefreshToken(
            admin_user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        db.add(db_token)
        await db.commit()


    async def delete_by_user_id(self, db: AsyncSession, user_id: UUID) -> None:
        await db.execute(
            delete(RefreshToken)
            .where(RefreshToken.admin_user_id == user_id)
        )
        await db.commit()


refresh_token_crud = CRUDRefreshToken(RefreshToken)