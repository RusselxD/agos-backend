from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.token import Token, TokenData
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.crud.admin_user import admin_user as admin_user_crud
from datetime import timedelta
from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter()

@router.post("/login", response_model=Token)
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()) -> Token:

    user_in_db = admin_user_crud.get_by_number(db, phone_number=form_data.username)

    if not user_in_db:
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
        "is_active": user_in_db.is_active
    }
    access_token = create_access_token(data=user_data_for_token, expires_delta=access_token_expires)  
    return {"access_token": access_token, "token_type": "bearer"}