from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.token import Token, TokenData
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.crud.admin_user import admin_user as admin_user_crud
from datetime import timedelta
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.schemas.auth import LoginRequest

router = APIRouter()

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)) -> Token:

    user_in_db = admin_user_crud.get_by_phone(db, phone_number=login_data.phone_number)

    if not user_in_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(login_data.password, user_in_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    user_data_for_token = {
        "sub": str(user_in_db.id), # Mandatory, used for identifying the user

        # Additional custom claims
        "is_superuser": user_in_db.is_superuser,
        "is_active": user_in_db.is_active,
        "force_password_change": user_in_db.force_password_change,
    }
    access_token = create_access_token(data=user_data_for_token, expires_delta=access_token_expires)  
    return {"access_token": access_token, "token_type": "bearer"}