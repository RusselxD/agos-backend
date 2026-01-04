from app.crud.responder import responder_otp_verification as responder_otp_verification_crud
from app.crud.responder import responder as responder_crud
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from app.models.responders_otp_verification import RespondersOTPVerification as OTPModel
from app.core.config import settings
from app.schemas import ResponderOTPVerificationCreate, ResponderOTPVerifyRequest, ResponderCreate
import random
from app.core.security import get_otp_hash, verify_otp

class ResponderService:

    """
        Return values:
        - bool: success or failure
        - str: message
        - bool: should send
    """
    async def verify_otp(self, verify_request: ResponderOTPVerifyRequest, db: AsyncSession) -> tuple[bool, str, bool]:
        
        record: OTPModel = await responder_otp_verification_crud.get_by_phone_number(db, verify_request.phone_number)
        if not record or not record.otp_hash:
            return False, "No OTP request found for this phone number.", True
        
        # expired OTP
        if record.expires_at < datetime.now(timezone.utc):
            await responder_otp_verification_crud.delete(db, obj=record)
            return False, "OTP has expired. Please request a new one.", True

        if not verify_otp(verify_request.otp, record.otp_hash):
            record.attempt_count += 1
            
            if record.attempt_count >= settings.OTP_ATTEMPT_LIMIT:
                await responder_otp_verification_crud.delete(db, obj=record)
                return False, "Too many incorrect attempts. Please request a new OTP.", True
            
            # Save the new attempt count
            await responder_otp_verification_crud.save_incremented_attempt_count(db=db, record=record)
            return False, "Incorrect OTP Code.", False

        # 3. Success Logic: Cleanup
        await responder_otp_verification_crud.delete(db, obj=record)
        return True, "", False

    async def send_otp(self, phone_number: str, db: AsyncSession) -> tuple[bool, str]:
        # 1. Check if we can send and get the existing record in one go
        can_send, message, existing_record = await self._can_send_otp(phone_number, db)
        if not can_send:
            return False, message
        
        # 2. If a record exists (but is valid to be replaced), delete it now
        if existing_record:
            await responder_otp_verification_crud.delete(db, obj=existing_record)
        
        # 3. Generate and Store
        otp = "".join(random.choices("0123456789", k=settings.OTP_LENGTH))
        otp_hash = get_otp_hash(otp)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        
        obj_in = ResponderOTPVerificationCreate(
            phone_number=phone_number,
            otp_hash=otp_hash,
            expires_at=expires_at,
        )
        await responder_otp_verification_crud.create(db=db, obj_in=obj_in)
        
        print(f"OTP for {phone_number}: {otp}") # Test only
        return True, "OTP sent successfully."

    async def _can_send_otp(self, phone_number: str, db: AsyncSession) -> tuple[bool, str, OTPModel | None]:
        # Check registration
        if await responder_crud.record_exists(db, phone_number):
            return False, "Phone number is already registered.", None

        record = await responder_otp_verification_crud.get_by_phone_number(db, phone_number)
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

    async def create_responder(self, responder_data: ResponderCreate, db: AsyncSession) -> None:
        await responder_crud.create(db=db, obj_in=responder_data)

responder_service = ResponderService()