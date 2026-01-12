from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.admin_user import admin_user as admin_user_crud
from app.core.security import verify_password, create_access_token
from fastapi import HTTPException, status
from app.core.config import settings
from datetime import timedelta
from app.schemas import Token
from datetime import datetime, timezone
from app.models.admin_user import AdminUser
from app.api.v1.dependencies import require_auth, CurrentUser

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

        access_token = self._create_token(user=user_in_db)
        return Token(access_token=access_token, token_type="bearer")

    async def change_user_password(self, db: AsyncSession, new_password: str, user: CurrentUser) -> Token:
        user_id = user.id
        user_in_db: AdminUser = await admin_user_crud.update_password(db=db, user_id=user_id, new_password=new_password)
        
        access_token = self._create_token(user=user_in_db)
        return Token(access_token=access_token, token_type="bearer")

    def _create_token(self, user: AdminUser) -> str:
        user_data_for_token = {
            "sub": str(user.id), # Mandatory, used for identifying the user

            # Additional custom claims
            "is_superuser": user.is_superuser,
            "is_enabled": user.is_enabled,
            "force_password_change": user.force_password_change,
        }

        access_token_expires = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
        access_token = create_access_token(data=user_data_for_token, expires_delta=access_token_expires)
        return access_token

auth_service = AuthService()