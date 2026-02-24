from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.dependencies import CurrentUser, require_auth
from app.core.database import get_db
from fastapi import Depends
from uuid import UUID
from app.schemas import ResponderCreate, ResponderDetailsResponse, ResponderListItem, ResponderDetails, NotifPreferenceUpdateRequest
from app.schemas import ResponderForApproval, ResponderOTPVerifyRequest, ResponderOTPVerifyResponse, ResponderSendSMSRequest, ResponderRegistrationRequest
from app.services import responder_service
from app.models.responder_related.responders import NotificationPreference

router = APIRouter(prefix="/responder", tags=["responder"])


@router.get("/all", dependencies=[Depends(require_auth)], response_model=list[ResponderListItem])
async def get_all_responders(db:AsyncSession = Depends(get_db)) -> list[ResponderListItem]:
    return await responder_service.get_all_responders(db=db)


@router.get("/additional-details/{responder_id}", dependencies=[Depends(require_auth)], response_model=ResponderDetailsResponse)
async def get_responder_details(responder_id: str, db:AsyncSession = Depends(get_db)) -> ResponderDetailsResponse:
    return await responder_service.get_responder_details(responder_id=responder_id, db=db)


@router.post("/bulk", response_model=list[ResponderListItem])
async def bulk_create_responders(
                            responders: list[ResponderCreate], 
                            db: AsyncSession = Depends(get_db),
                            user: CurrentUser = Depends(require_auth)) -> list[ResponderListItem]:
    return await responder_service.bulk_create_responders(responders=responders, db=db, user_id=user.id)


# ========================== ================= ==========================
# ========================== ================= ==========================
# ========================== FOR RESPONDER APP ==========================
# ========================== ================= ==========================
# ========================== ================= ==========================

@router.get("/{responder_id}", response_model=ResponderDetails)
async def get_responder_details_for_app(responder_id: UUID, db:AsyncSession = Depends(get_db)) -> ResponderDetails:
    return await responder_service.get_responder_details_for_app(responder_id=responder_id, db=db)


@router.get("/notif-preferences/{responder_id}", response_model=NotificationPreference)
async def get_responder_notif_preferences(responder_id: UUID, db:AsyncSession = Depends(get_db)) -> NotificationPreference:
    return await responder_service.get_responder_notif_preferences(responder_id=responder_id, db=db)


@router.put("/notif-preferences/{responder_id}", status_code=204)
async def update_responder_notif_preferences(responder_id: UUID, request: NotifPreferenceUpdateRequest, db:AsyncSession = Depends(get_db)) -> None:
    await responder_service.update_responder_notif_preferences(
        responder_id=responder_id, key=request.key, value=request.value, db=db
    )


@router.post("/for-approval", response_model=ResponderForApproval)
async def get_responder_for_approval(request: ResponderRegistrationRequest, db: AsyncSession = Depends(get_db)) -> ResponderForApproval:
    return await responder_service.get_responder_for_approval(phone_number=request.phone_number, db=db)


@router.post("/resend-otp/{responder_id}", status_code=204)
async def resend_otp(responder_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await responder_service.resend_otp(responder_id=responder_id, db=db)


@router.post("/verify-otp", response_model=ResponderOTPVerifyResponse)
async def verify_otp(verify_request: ResponderOTPVerifyRequest, db: AsyncSession = Depends(get_db)) -> ResponderOTPVerifyResponse:
    return await responder_service.verify_otp(verify_request=verify_request, db=db)


@router.post("/send-sms", status_code=204)
async def send_sms(send_request: ResponderSendSMSRequest, db: AsyncSession = Depends(get_db)) -> None:
    await responder_service.send_sms(send_request=send_request, db=db)