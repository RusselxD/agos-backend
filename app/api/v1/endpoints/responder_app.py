from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from fastapi import Depends
from uuid import UUID
from app.schemas import ResponderDetails, NotifPreferenceUpdateRequest, AlertListItem
from app.schemas import ResponderForApproval, ResponderOTPVerifyRequest, ResponderOTPVerifyResponse, ResponderSendSMSRequest, ResponderRegistrationRequest
from app.schemas import AcknowledgeNotifRequest, AcknowledgeNotifResponse
from app.models.responder_related.responders import NotificationPreference
from app.services import responder_app_service

router = APIRouter(prefix="/responder", tags=["responder app"])


@router.get("/{responder_id}", response_model=ResponderDetails)
async def get_responder_details_for_app(
    responder_id: UUID, 
    db:AsyncSession = Depends(get_db)) -> ResponderDetails:

    return await responder_app_service.get_responder_details_for_app(responder_id=responder_id, db=db)


@router.get("/unread-alerts-count/{responder_id}", response_model=int)
async def get_unread_alerts_count(
    responder_id: UUID, 
    db: AsyncSession = Depends(get_db)) -> int:

    return await responder_app_service.get_unread_alerts_count(responder_id=responder_id, db=db)


@router.get("/alerts/{responder_id}", response_model=list[AlertListItem])
async def get_responder_alerts(
    responder_id: UUID, 
    db: AsyncSession = Depends(get_db)):

    return await responder_app_service.get_responder_alerts(responder_id=responder_id, db=db)


@router.post("/acknowledge-alert", response_model=AcknowledgeNotifResponse)
async def acknowledge_alert(
    payload: AcknowledgeNotifRequest, 
    db: AsyncSession = Depends(get_db)) -> AcknowledgeNotifResponse:

    return await responder_app_service.acknowledge_alert(payload=payload, db=db)


@router.get("/notif-preferences/{responder_id}", response_model=NotificationPreference)
async def get_responder_notif_preferences(
    responder_id: UUID, 
    db:AsyncSession = Depends(get_db)) -> NotificationPreference:

    return await responder_app_service.get_responder_notif_preferences(responder_id=responder_id, db=db)


@router.put("/notif-preferences/{responder_id}", status_code=204)
async def update_responder_notif_preferences(
    responder_id: UUID, 
    request: NotifPreferenceUpdateRequest, 
    db:AsyncSession = Depends(get_db)) -> None:

    await responder_app_service.update_responder_notif_preferences(
        responder_id=responder_id, key=request.key, value=request.value, db=db
    )


@router.post("/for-approval", response_model=ResponderForApproval)
async def get_responder_for_approval(
    request: ResponderRegistrationRequest, 
    db: AsyncSession = Depends(get_db)) -> ResponderForApproval:

    return await responder_app_service.get_responder_for_approval(phone_number=request.phone_number, db=db)


@router.post("/resend-otp/{responder_id}", status_code=204)
async def resend_otp(responder_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    await responder_app_service.resend_otp(responder_id=responder_id, db=db)


@router.post("/verify-otp", response_model=ResponderOTPVerifyResponse)
async def verify_otp(
    verify_request: ResponderOTPVerifyRequest, 
    db: AsyncSession = Depends(get_db)) -> ResponderOTPVerifyResponse:
    
    return await responder_app_service.verify_otp(verify_request=verify_request, db=db)


@router.post("/send-sms", status_code=204)
async def send_sms(send_request: ResponderSendSMSRequest, db: AsyncSession = Depends(get_db)) -> None:
    await responder_app_service.send_sms(send_request=send_request, db=db)