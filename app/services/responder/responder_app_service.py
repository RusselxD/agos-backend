from fastapi import HTTPException
from app.crud import notification_delivery_crud
from app.crud import responder_otp_verification_crud
from app.crud.responder_group import responder_group_crud
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.models import NotificationDelivery
from uuid import UUID
import random
from app.schemas import ResponderDetails, ResponderOTPVerificationCreate, ResponderOTPVerifyRequest, ResponderSendSMSRequest
from app.models.responder_related.responders import NotificationPreference
from app.schemas.responder import ResponderForApproval
from app.services.sms_service import sms_service
from app.core.exceptions import SMSError
from app.crud import acknowledgement_crud
from app.models import Acknowledgement
from app.core.security import get_otp_hash, verify_otp as verify_otp_hash, create_responder_token
from app.models import Responder
from app.crud.responder import responder_crud
from app.schemas import ResponderOTPVerifyResponse, AlertListItem, AlertPaginatedResponse
from app.models.notification_template import NotificationType
from app.models.responder_related.group import DEFAULT_ACTIVE_RESPONDERS_GROUP_NAME
from app.schemas import AcknowledgeNotifRequest, AcknowledgeNotifResponse
from app.models.responder_related.responders import ResponderStatus


class ResponderAppService:
    

    async def get_responder_for_approval(self, phone_number: str, db: AsyncSession) -> ResponderForApproval | None:
        responder: Responder = await responder_crud.get_by_phone_number(db=db, phone_number=phone_number)

        if not responder:
            raise HTTPException(status_code=404, detail="Phone number not registered.")
        
        await self.send_otp(responder=responder, db=db)

        return ResponderForApproval(
            responder_id=responder.id,
            first_name=responder.first_name,
            last_name=responder.last_name,
            phone_number=responder.phone_number,
            status=responder.status
        )


    async def get_responder_details_for_app(self, responder_id: UUID, db: AsyncSession) -> ResponderDetails:
        responder: Responder = await responder_crud.get_responder_details_for_app(db=db, responder_id=responder_id)
        
        if not responder:
            raise HTTPException(status_code=404, detail="Responder not found.")
        
        return ResponderDetails(
            id=str(responder.id),
            first_name=responder.first_name,
            last_name=responder.last_name,
            status=responder.status,
            phone_number=responder.phone_number,
            location_id=responder.location_id,
            location_name=responder.location.name,
            created_at=responder.created_at,
            activated_at=responder.activated_at
        )


    async def get_unread_alerts_count(self, responder_id: UUID, db: AsyncSession) -> int:
        return await notification_delivery_crud.get_unread_alerts_count(
            responder_id=responder_id,
            db=db,
        )


    async def get_responder_alerts(
        self,
        responder_id: UUID,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        notification_type: NotificationType | None = None,
    ) -> AlertPaginatedResponse:
        deliveries, has_more = await notification_delivery_crud.get_alerts_per_responder(
            responder_id=responder_id,
            db=db,
            page=page,
            page_size=page_size,
            notification_type=notification_type,
        )

        return AlertPaginatedResponse(
            items=[
                AlertListItem(
                    id=delivery.id,
                    type=delivery.dispatch.type,
                    title=delivery.dispatch.title,
                    message=delivery.dispatch.message,
                    timestamp=delivery.sent_at,
                    is_acknowledged=delivery.acknowledgement is not None,
                    acknowledged_at=delivery.acknowledgement.acknowledged_at if delivery.acknowledgement else None,
                    acknowledge_message=delivery.acknowledgement.message if delivery.acknowledgement else None
                ) for delivery in deliveries
            ],
            has_more=has_more,
        )


    async def acknowledge_alert(self, payload: AcknowledgeNotifRequest, db: AsyncSession) -> AcknowledgeNotifResponse:
        ack: Acknowledgement = await acknowledgement_crud.create_acknowledgement(
            responder_id=payload.responder_id,
            delivery_id=payload.delivery_id,
            message=payload.message,
            db=db
        )
        return AcknowledgeNotifResponse(
            acknowledged_at=ack.acknowledged_at,
            acknowledge_message=ack.message
        )


    async def get_responder_notif_preferences(self, responder_id: UUID, db: AsyncSession) -> NotificationPreference:
        responder: Responder = await responder_crud.get(db=db, id=responder_id)
        
        if not responder:
            raise HTTPException(status_code=404, detail="Responder not found.")
        
        return responder.notif_preferences


    async def update_responder_notif_preferences(
        self, responder_id: UUID, key: str, value: bool, db: AsyncSession
    ) -> None:
        responder: Responder = await responder_crud.get(db=db, id=responder_id)
        if not responder:
            raise HTTPException(status_code=404, detail="Responder not found.")

        prefs = responder.notif_preferences
        responder.notif_preferences = prefs.model_copy(update={key: value})
        db.add(responder)
        await db.commit()


    async def send_otp(self, responder: Responder, db: AsyncSession) -> None:

        # Generate OTP
        otp = "".join(random.choices("0123456789", k=settings.OTP_LENGTH))
        print(f"[OTP] {responder.phone_number}: {otp}")
        otp_hash = get_otp_hash(otp=otp)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        
        # Store OTP (upsert: deletes existing and creates new)
        obj_in = ResponderOTPVerificationCreate(
            responder_id=responder.id,
            otp_hash=otp_hash,
            expires_at=expires_at,
        )
        await responder_otp_verification_crud.upsert_otp(db=db, obj_in=obj_in)
        
        # Send SMS
        try:
            await sms_service.send_one_sms(
                phone_number=responder.phone_number,
                message=f"Your AGOS OTP code is: {otp}"
            )
        except SMSError as e:
            raise HTTPException(status_code=503, detail=str(e))


    async def resend_otp(self, responder_id: UUID, db: AsyncSession) -> None:
        responder = await responder_crud.get(db=db, id=responder_id)
        
        if not responder:
            raise HTTPException(status_code=404, detail="Responder not found.")
        
        await self.send_otp(responder=responder, db=db)


    async def verify_otp(self, verify_request: ResponderOTPVerifyRequest, db: AsyncSession):
        # Get active group first (this may commit internally, so do it before transaction)
        active_group = await responder_group_crud.ensure_exists(db=db, name=DEFAULT_ACTIVE_RESPONDERS_GROUP_NAME)
        
        record = await responder_otp_verification_crud.get_by_responder_id(
            db=db, 
            responder_id=verify_request.responder_id
        )
        
        if not record:
            return ResponderOTPVerifyResponse(
                success=False,
                message="No OTP request found. Please request a new one.",
                requires_resend=True
            )
        
        # Check expiration
        if record.expires_at < datetime.now(timezone.utc):
            await responder_otp_verification_crud.delete_by_responder_id(db=db, responder_id=verify_request.responder_id)
            return ResponderOTPVerifyResponse(
                success=False,
                message="OTP has expired. Please request a new one.",
                requires_resend=True
            )
        
        # Verify OTP
        if not verify_otp_hash(plain_otp=verify_request.otp, hashed_otp=record.otp_hash):
            if record.attempt_count + 1 >= settings.OTP_ATTEMPT_LIMIT:
                await responder_otp_verification_crud.delete_by_responder_id(db=db, responder_id=verify_request.responder_id)
                return ResponderOTPVerifyResponse(
                    success=False,
                    message="Too many incorrect attempts. Please request a new OTP.",
                    requires_resend=True
                )
            
            await responder_otp_verification_crud.increment_attempt_count(db=db, record=record)
            return ResponderOTPVerifyResponse(
                success=False,
                message="Incorrect OTP code.",
                requires_resend=False  # Can still retry
            )
        
        # Success - activate and add to group only if still pending (active responders re-logging in skip this)
        responder = await responder_crud.get(db=db, id=verify_request.responder_id)
        if responder.status == ResponderStatus.PENDING:
            await responder_crud.activate(db=db, responder_id=verify_request.responder_id, commit=False)
            await responder_group_crud.add_member(db=db, group_id=active_group.id, responder_id=verify_request.responder_id, commit=False)
        await responder_otp_verification_crud.delete_by_responder_id(db=db, responder_id=verify_request.responder_id)

        token = create_responder_token(str(verify_request.responder_id))

        return ResponderOTPVerifyResponse(
            success=True,
            message="OTP verified successfully.",
            requires_resend=False,
            responder_token=token,
        )


    async def send_sms(self, send_request: ResponderSendSMSRequest, db: AsyncSession) -> None:
        """Send SMS to multiple responders. Fails if any responder ID is invalid."""
        responders = await responder_crud.get_by_ids(db=db, ids=send_request.responder_ids)
        
        if len(responders) != len(send_request.responder_ids):
            raise HTTPException(
                status_code=404, 
                detail="One or more responder IDs not found."
            )
        
        phone_numbers = [responder.phone_number for responder in responders]

        try:
            result = await sms_service.send_bulk_sms(
                phone_numbers=phone_numbers,
                message=send_request.message
            )
        except SMSError as e:
            raise HTTPException(status_code=503, detail=str(e))

        if result["failed"]:
            failed_count = len(result["failed"])
            total_count = len(phone_numbers)
            raise HTTPException(
                status_code=207,
                detail=f"SMS partially delivered: {total_count - failed_count}/{total_count} succeeded."
            )


responder_app_service = ResponderAppService()
