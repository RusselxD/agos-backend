from fastapi import HTTPException
from app.api.v1.dependencies import CurrentUser
from app.crud.responder import responder_otp_verification as responder_otp_verification_crud
from app.crud.responder import responder as responder_crud
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from app.models import RespondersOTPVerification as OTPModel
from app.core.config import settings
from app.schemas import ResponderOTPVerificationCreate, ResponderOTPVerifyRequest, ResponderCreate
import random
from app.core.security import get_otp_hash, verify_otp
from app.schemas import ResponderListItem, ResponderDetailsResponse
from app.schemas.admin_audit_log import AdminAuditLogCreate
from app.crud.admin_audit_log import admin_audit_log as admin_audit_log_crud
from app.models import Responders as Responder
from app.utils import format_name_proper
from app.services.sms_service import sms_service

class ResponderService:

    """
        Return values:
        - bool: success or failure
        - str: message
        - bool: should send
    """
    async def verify_otp(self, verify_request: ResponderOTPVerifyRequest, db: AsyncSession) -> tuple[bool, str, bool]:
        
        record: OTPModel = await responder_otp_verification_crud.get_by_phone_number(db=db, 
                                                                                    phone_number=verify_request.phone_number)
        if not record or not record.otp_hash:
            return False, "No OTP request found for this phone number.", True
        
        # expired OTP
        if record.expires_at < datetime.now(timezone.utc):
            await responder_otp_verification_crud.delete(db=db, obj=record)
            return False, "OTP has expired. Please request a new one.", True

        if not verify_otp(plain_otp=verify_request.otp, hashed_otp=record.otp_hash):
            record.attempt_count += 1
            
            if record.attempt_count >= settings.OTP_ATTEMPT_LIMIT:
                await responder_otp_verification_crud.delete(db=db, obj=record)
                return False, "Too many incorrect attempts. Please request a new OTP.", True
            
            # Save the new attempt count
            await responder_otp_verification_crud.save_incremented_attempt_count(db=db, record=record)
            return False, "Incorrect OTP Code.", False

        # 3. Success Logic: Cleanup
        await responder_otp_verification_crud.delete(db=db, obj=record)
        return True, "", False

    async def send_otp(self, phone_number: str, db: AsyncSession) -> tuple[bool, str]:
        # 1. Check if we can send and get the existing record in one go
        can_send, message, existing_record = await self._can_send_otp(phone_number, db=db)
        if not can_send:
            return False, message
        
        # 2. If a record exists (but is valid to be replaced), delete it now
        if existing_record:
            await responder_otp_verification_crud.delete(db=db, obj=existing_record)
        
        # 3. Generate and Store
        otp = "".join(random.choices("0123456789", k=settings.OTP_LENGTH))
        otp_hash = get_otp_hash(otp=otp)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        
        obj_in = ResponderOTPVerificationCreate(
            phone_number=phone_number,
            otp_hash=otp_hash,
            expires_at=expires_at,
        )
        await responder_otp_verification_crud.create_only(db=db, obj_in=obj_in)
        
        await sms_service.send_one_sms(phone_number=phone_number, message=f"Your OTP code is: {otp}")
        return True, "OTP sent successfully."

    async def _can_send_otp(self, phone_number: str, db: AsyncSession) -> tuple[bool, str, OTPModel | None]:
        # Check registration
        if await responder_crud.record_exists(db=db, phone_number=phone_number):
            return False, "Phone number is already registered.", None

        record = await responder_otp_verification_crud.get_by_phone_number(db=db, phone_number=phone_number)
        if not record:
            return True, "", None

        now = datetime.now(timezone.utc)
        
        # Case 1: Expired - can be deleted
        if record.expires_at < now:
            return True, "", record # Let send_otp delete it

        # Case 2: Cooldown check
        time_since_send = (now - record.created_at).total_seconds()
        if time_since_send < settings.OTP_RESEND_COOLDOWN_SECONDS:
            wait = int(settings.OTP_RESEND_COOLDOWN_SECONDS - time_since_send)
            return False, f"Too many requests. Please wait {wait} seconds.", None

        # Case 3: Too many attempts but not expired
        if record.attempt_count >= settings.OTP_ATTEMPT_LIMIT:
            # Check if they are still in a "locked out" period based on created_at
            # or just allow a resend if cooldown is over. 
            return True, "", record

        # Case 4: Valid record exists, but cooldown passed - allow replacement
        return True, "", record

    async def get_all_responders(self, db: AsyncSession) -> list[ResponderListItem]:
        responders = await responder_crud.get_all(db=db)
        result = [
            ResponderListItem(
                id=responder.id,
                first_name=responder.first_name,
                last_name=responder.last_name,
                phone_number=responder.phone_number,
                status=responder.status,
                groups=[group.name for group in responder.groups]
            ) for responder in responders
        ]
        return result
    
    async def create_responder(self, responder_data: ResponderCreate, db: AsyncSession) -> None:
        # format names properly
        responder_data.first_name = format_name_proper(responder_data.first_name)
        responder_data.last_name = format_name_proper(responder_data.last_name)

        await responder_crud.create_only(db=db, obj_in=responder_data)

    async def get_responder_details(self, responder_id: str, db: AsyncSession) -> ResponderDetailsResponse | None:
        responder: Responder = await responder_crud.get_details(db=db, id=responder_id)
        
        if not responder:
            raise HTTPException(status_code=404, detail="Responder not found.")
        
        return ResponderDetailsResponse(
            id=responder.id,
            first_name=responder.first_name,
            last_name=responder.last_name,
            phone_number=responder.phone_number,
            id_photo_path=responder.id_photo_path,
            status=responder.status,
            created_at=responder.created_at,
            approved_by=f"{responder.admin_user.first_name} {responder.admin_user.last_name}" if responder.approved_by else None,
            approved_at=responder.approved_at
        )

    async def approve_responder_registration(self, responder_id: str, db: AsyncSession, user: CurrentUser) -> None:
        responder: Responder = await responder_crud.get_with_lock(db=db, id=responder_id)
        
        if not responder:
            raise HTTPException(status_code=404, detail="Responder not found.")
        
        if responder.status == 'approved':
            raise HTTPException(status_code=400, detail="Responder is already approved.")

        await responder_crud.approve_responder(db=db, responder=responder, user_id=user.id)

        # Log the admin who approved
        await admin_audit_log_crud.create_only(
            db=db,
            obj_in=AdminAuditLogCreate(
                admin_user_id=user.id,
                action=f"Approved {responder.first_name} {responder.last_name} for responder"
            )
        )

        await db.commit()  # Commit here for idempotency

responder_service = ResponderService()
