from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.user import User, RoleEnum
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    UserOut,
    TokenResponse,
    OTPRequest,
    OTPResetPassword,
)
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    generate_otp,
)
from app.api.deps import require_auth

router = APIRouter(prefix="/auth", tags=["1. Authentication & Login"])

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists.")
    
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role or RoleEnum.WAREHOUSE_STAFF,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is deactivated.")

    token = create_access_token({"sub": str(user.id), "role": user.role.value, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/request-otp")
def request_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Avoid user enumeration in production, but confirm email received
        return {"message": "If the account exists, an OTP has been sent."}

    otp = generate_otp()
    user.otp_code = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    db.commit()

    # In production this triggers an SMS/Email service (e.g. Twilio / SendGrid)
    return {
        "message": f"OTP successfully generated and sent to {payload.email}.",
        "dev_debug_otp": otp # Provided for smooth local testing and demoing
    }

@router.post("/reset-password-otp")
def reset_password_with_otp(payload: OTPResetPassword, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP request.")

    if datetime.utcnow() > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    if user.otp_code != payload.otp.strip():
        raise HTTPException(status_code=400, detail="Incorrect OTP.")

    user.hashed_password = hash_password(payload.new_password)
    user.otp_code = None
    user.otp_expires_at = None
    db.commit()

    return {"message": "Password successfully reset. You may now log in with your new password."}

@router.get("/me", response_model=UserOut)
def get_current_user_profile(user: User = Depends(require_auth)):
    return user
