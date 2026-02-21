import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import verify_password, create_access_token
from fastapi import HTTPException, status
from app.core.config import settings
from datetime import timedelta
from app.schemas import Token, AdminAuditLogCreate
from datetime import datetime, timezone
from app.models.admin_user import AdminUser
from app.api.v1.dependencies import CurrentUser
from app.crud import admin_user_crud
from app.crud import admin_audit_log_crud
from app.crud import refresh_token_crud

class AuthService:
    
    async def authenticate_user(self, db: AsyncSession, phone_number: str, password: str) -> Token:

        user_in_db = await admin_user_crud.get_by_phone(db=db, phone_number=phone_number)

        if not user_in_db or not verify_password(plain_password=password, hashed_password=user_in_db.hashed_password):
            raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid credentials",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
        
        # Update last login
        await admin_user_crud.update_last_login(db=db, user=user_in_db, last_login=datetime.now(timezone.utc))

        access_token = self._create_access_token(user=user_in_db)
        refresh_token = await self._create_refresh_token(db=db, user=user_in_db)
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


    async def logout_user(self, db: AsyncSession, user_id: str) -> None:
        # Invalidate all refresh tokens for the user
        await refresh_token_crud.delete_by_user_id(db=db, user_id=user_id)


    async def refresh_access_token(self, db: AsyncSession, refresh_token: str) -> Token:

        token_in_db = await refresh_token_crud.get_by_token(db=db, token=refresh_token)

        if not token_in_db:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        if token_in_db.expires_at < datetime.now(timezone.utc):
            await db.delete(token_in_db)
            await db.commit()
            raise HTTPException(status_code=401, detail="Refresh token expired, please login again")
        
        # store the user before deleting the token
        user = token_in_db.admin_user

        # Delete the used refresh token to prevent reuse
        await db.delete(token_in_db)
        await db.commit()

        # issue new token
        new_access_token = self._create_access_token(user=user)
        new_refresh_token = await self._create_refresh_token(db=db, user=user)

        return Token(access_token=new_access_token, refresh_token=new_refresh_token, token_type="bearer")


    async def change_user_password(self, db: AsyncSession, new_password: str, user: CurrentUser) -> Token:
        user_id = user.id
        user_in_db: AdminUser = await admin_user_crud.update_password(db=db, user_id=user_id, new_password=new_password)
        
        # Log the password change action
        await admin_audit_log_crud.create_only(
            db=db,
            obj_in=AdminAuditLogCreate(
                admin_user_id=user.id,
                action="Changed password"
            )
        )

        access_token = self._create_access_token(user=user_in_db)
        refresh_token = await self._create_refresh_token(db=db, user=user_in_db)
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


    def _create_access_token(self, user: AdminUser) -> str:
        user_data_for_token = {
            "sub": str(user.id), # Mandatory, used for identifying the user

            # Additional custom claims
            "is_superuser": user.is_superuser,
            "is_enabled": user.is_enabled,
            "force_password_change": user.force_password_change,
        }

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data=user_data_for_token, expires_delta=access_token_expires)
        return access_token


    async def _create_refresh_token(self, db: AsyncSession, user: AdminUser) -> str:
        token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await refresh_token_crud.create(user_id=user.id, token=token, expires_at=expires_at, db=db)
        return token


auth_service = AuthService()