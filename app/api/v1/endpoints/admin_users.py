from fastapi import APIRouter
from app.schemas import AdminUserResponse, AdminUserCreate
from app.schemas.admin_user import AdminDeactivateRequest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.admin_user_service import admin_user_service
from fastapi import Depends
from app.core.database import get_db
from app.api.v1.dependencies import require_auth, require_superuser, CurrentUser

router = APIRouter( prefix="/admin-users", tags=["admin-users"])


@router.get("/", response_model=list[AdminUserResponse], dependencies=[Depends(require_auth)])
async def get_all_admins(db: AsyncSession = Depends(get_db)) -> list[AdminUserResponse]:
    return await admin_user_service.get_all_admins(db=db)


@router.post("/", response_model=AdminUserResponse)
async def create_admin_user(
    admin_user_create: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser)) -> AdminUserResponse:

    return await admin_user_service.create_new_admin_user(db=db, admin_user_create=admin_user_create, current_user=current_user)


@router.put("/{user_id}/deactivate", status_code=204)
async def deactivate_admin(
    user_id: str,
    request: AdminDeactivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser),
) -> None:
    await admin_user_service.deactivate_admin(
        db=db, user_id=user_id, current_user=current_user, reason=request.reason
    )


@router.put("/{user_id}/reactivate", status_code=204)
async def reactivate_admin(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser),
) -> None:
    await admin_user_service.reactivate_admin(
        db=db, user_id=user_id, current_user=current_user
    )
