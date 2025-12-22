from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.admin_user import admin_user as admin_user_crud
from app.core.security import verify_password, create_access_token
from fastapi import HTTPException, status
from app.core.config import settings
from datetime import timedelta
from app.schemas.token import Token
from datetime import datetime, timezone


class AuthService:
    
    async def authenticate_user(self, db: AsyncSession, phone_number: str, password: str) -> Token:

        user_in_db = await admin_user_crud.get_by_phone(db, phone_number=phone_number)

        if not user_in_db or not verify_password(password, user_in_db.hashed_password):
            raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid credentials",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

        access_token_expires = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
        user_data_for_token = {
            "sub": str(user_in_db.id), # Mandatory, used for identifying the user

            # Additional custom claims
            "is_superuser": user_in_db.is_superuser,
            "is_active": user_in_db.is_active,
            "force_password_change": user_in_db.force_password_change,
        }

        # Update last login
        user_in_db.last_login = datetime.now(timezone.utc)
        await db.commit()

        access_token = create_access_token(data=user_data_for_token, expires_delta=access_token_expires)
        return Token(access_token=access_token, token_type="bearer")

auth_service = AuthService()