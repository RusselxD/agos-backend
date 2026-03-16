import secrets

from fastapi import Depends,Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.crud import admin_user_crud

security = HTTPBearer()
iot_api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

class CurrentUser:
    
    """Holds the authenticated user's data from the token"""
    def __init__(self, id: str, is_superuser: bool, is_enabled: bool, force_password_change: bool):
        self.id = id
        self.is_superuser = is_superuser
        self.is_enabled = is_enabled
        self.force_password_change = force_password_change


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)) -> CurrentUser:

    """Check if user is logged in (has valid token)"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        is_superuser = payload.get("is_superuser", False)
        is_enabled = payload.get("is_enabled", False)
        force_password_change = payload.get("force_password_change", False)
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_in_db = await admin_user_crud.get(db, id=user_id)
    if user_in_db is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user_in_db.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return CurrentUser(
        id=user_id,
        is_superuser=is_superuser,
        is_enabled=is_enabled,
        force_password_change=force_password_change
    )


async def require_superuser(
    current_user: CurrentUser = Depends(require_auth)) -> CurrentUser:
    
    """Check if user is logged in AND is a superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    return current_user


async def require_iot_api_key(x_api_key: str | None = Depends(iot_api_key_header)) -> None:
    """Validate static API key used by trusted IoT devices."""
    expected = settings.IOT_API_KEY

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="IOT_API_KEY is not configured",
        )

    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )