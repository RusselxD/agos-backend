from fastapi import APIRouter
from app.schemas import AdminUserResponse, AdminUserCreate
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.admin_user_service import admin_user_service
from fastapi import Depends
from app.core.database import get_db
from app.api.v1.dependencies import require_auth, require_superuser, CurrentUser

router = APIRouter()

@router.get("/", response_model=list[AdminUserResponse], dependencies=[Depends(require_auth)])
async def get_all_admins(db: AsyncSession = Depends(get_db)) -> list[AdminUserResponse]:
    return await admin_user_service.get_all_admins(db=db)

@router.post("/", response_model=AdminUserResponse)
async def create_admin_user(admin_user_create: AdminUserCreate, 
                            db: AsyncSession = Depends(get_db),
                            current_user: CurrentUser = Depends(require_superuser)
                            ) -> AdminUserResponse:
    
    return await admin_user_service.create_new_admin_user(db=db, admin_user_create=admin_user_create, current_user=current_user)