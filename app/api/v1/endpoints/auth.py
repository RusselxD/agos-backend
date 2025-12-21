from fastapi import APIRouter, Depends
from app.schemas.token import Token
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.auth_service import auth_service
from app.schemas.auth import LoginRequest

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    return await auth_service.authenticate_user(db, login_data.phone_number, login_data.password)