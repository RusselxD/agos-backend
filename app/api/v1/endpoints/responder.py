from fastapi import APIRouter, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from fastapi import Depends
from app.schemas import ResponderOTPRequest, ResponderOTPResponse, ResponderOTPVerifyRequest, ResponderOTPVerifyResponse, UploadResponse, ResponderCreate
from app.services import responder_service, upload_service

router = APIRouter()

@router.post("/send-otp", response_model=ResponderOTPResponse)
async def send_otp(otp_request:ResponderOTPRequest, db: AsyncSession = Depends(get_db)) -> ResponderOTPResponse:
    is_success, message = await responder_service.send_otp(phone_number=otp_request.phone_number, db=db)
    return ResponderOTPResponse(
        success=is_success, 
        message=message
    )

@router.post("/verify-otp", response_model=ResponderOTPVerifyResponse)
async def verify_otp(verify_request: ResponderOTPVerifyRequest, 
                    db: AsyncSession = Depends(get_db)) -> ResponderOTPVerifyResponse:
    
    is_success, message, send_again = await responder_service.verify_otp(verify_request=verify_request, db=db)
    
    return ResponderOTPVerifyResponse(
        success=is_success, 
        message=message, 
        send_again=send_again
    )

@router.post("/upload-id-photo", response_model=UploadResponse)
async def upload_responder_id_photo(file: UploadFile = File(...)) -> UploadResponse:
    file_path = await upload_service.upload_responder_id_photo(file=file)
    return UploadResponse(
        file_path=file_path
    )

@router.post("/create", status_code=204)
async def create_responder(responder_data: ResponderCreate, db: AsyncSession = Depends(get_db)) -> None:
    await responder_service.create_responder(responder_data=responder_data, db=db)