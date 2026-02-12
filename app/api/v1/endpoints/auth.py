from fastapi import APIRouter, Depends, Request
from app.schemas import Token
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services import auth_service
from app.schemas import LoginRequest, ChangePasswordRequest
from app.api.v1.dependencies import require_auth, CurrentUser
from app.core.rate_limiter import limiter

router = APIRouter( prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request, 
    login_data: LoginRequest, 
    db: AsyncSession = Depends(get_db)) -> Token:
    
    return await auth_service.authenticate_user(db=db, 
                                                phone_number=login_data.phone_number, 
                                                password=login_data.password)


# Force password change endpoint
@router.post("/change-password", response_model=Token)
@limiter.limit("3/minute")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest, 
    db: AsyncSession = Depends(get_db), 
    user: CurrentUser = Depends(require_auth)) -> Token:
    
    return await auth_service.change_user_password(db=db, new_password=password_data.new_password, user=user)