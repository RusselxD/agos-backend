from fastapi import HTTPException
from app.crud.responder import responder_crud, responder_otp_verification_crud
from app.crud.responder_group import responder_group_crud
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from uuid import UUID
import random
from app.core.security import get_otp_hash, verify_otp as verify_otp_hash
from app.models import Responder
from app.models.responder_related.group import DEFAULT_ACTIVE_RESPONDERS_GROUP_NAME
from app.models.responder_related.responders import ResponderStatus
from app.schemas import ResponderListItem, ResponderDetailsResponse, ResponderOTPVerifyResponse
from app.schemas.responder import ResponderCreate, ResponderDetails, ResponderForApproval, ResponderOTPVerificationCreate, ResponderOTPVerifyRequest, ResponderSendSMSRequest
from app.services.sms_service import sms_service


class ResponderService:

    async def get_all_responders(self, db: AsyncSession) -> list[ResponderListItem]:
        responders = await responder_crud.get_all(db=db)
        return responders
    

    async def get_responder_details(self, responder_id: str, db: AsyncSession) -> ResponderDetailsResponse | None:
        responder: Responder = await responder_crud.get_details(db=db, id=responder_id)
        
        if not responder:
            raise HTTPException(status_code=404, detail="Responder not found.")
        
        return ResponderDetailsResponse(
            created_at=responder.created_at,
            created_by=f"{responder.admin_user.first_name} {responder.admin_user.last_name}",
            activated_at=responder.activated_at
        )
    

    async def bulk_create_responders(self, responders: list[ResponderCreate], db: AsyncSession, user_id: str) -> list[ResponderListItem]:
        created_responders = await responder_crud.bulk_create_and_return(db=db, objs_in=responders, created_by_id=user_id)
        return [
            ResponderListItem(
                id=responder.id,
                first_name=responder.first_name,
                last_name=responder.last_name,
                phone_number=responder.phone_number,
                status=responder.status,
                groups=[group.name for group in responder.groups]
            ) for responder in created_responders
        ]


    async def get_responder_for_approval(self, phone_number: str, db: AsyncSession) -> ResponderForApproval | None:
        responder: Responder = await responder_crud.get_by_phone_number(db=db, phone_number=phone_number)

        if not responder:
            raise HTTPException(status_code=404, detail="Phone number not registered.")
        
        # send otp if already exists
        if responder.status == ResponderStatus.PENDING:
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


    async def send_otp(self, responder: Responder, db: AsyncSession) -> None:

        # Generate OTP
        otp = "".join(random.choices("0123456789", k=settings.OTP_LENGTH))
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
        await sms_service.send_one_sms(
            phone_number=responder.phone_number, 
            message=f"Your AGOS OTP code is: {otp}"
        )


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
        
        # Success - activate responder, add to active group, and cleanup OTP record
        await responder_crud.activate(db=db, responder_id=verify_request.responder_id, commit=False)
        await responder_group_crud.add_member(db=db, group_id=active_group.id, responder_id=verify_request.responder_id, commit=False)
        await responder_otp_verification_crud.delete_by_responder_id(db=db, responder_id=verify_request.responder_id)
        
        return ResponderOTPVerifyResponse(
            success=True,
            message="OTP verified successfully.",
            requires_resend=False
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
        await sms_service.send_bulk_sms(
            phone_numbers=phone_numbers, 
            message=send_request.message
        )


responder_service = ResponderService()