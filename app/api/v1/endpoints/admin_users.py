from fastapi import APIRouter
from app.schemas import AdminUserResponse
from typing import List
from app.crud.admin_user import admin_user as admin_user_crud
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from fastapi import Depends

router = APIRouter()

@router.get("/", response_model=List[AdminUserResponse])
async def get_all_admins(db: AsyncSession = Depends(get_db)) -> List[AdminUserResponse]:
    return await admin_user_crud.get_all(db=db)