from fastapi import APIRouter, Depends
from app.schemas import Token
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services import auth_service
from app.schemas import LoginRequest, ChangePasswordRequest
from app.api.v1.dependencies import require_auth, CurrentUser

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    return await auth_service.authenticate_user(db=db, 
                                                phone_number=login_data.phone_number, 
                                                password=login_data.password)

@router.post("/change-password", response_model=Token)
async def change_password(
    request: ChangePasswordRequest, 
    db: AsyncSession = Depends(get_db), 
    user: CurrentUser = Depends(require_auth)) -> Token:
    
    return await auth_service.change_user_password(db=db, new_password=request.new_password, user=user)