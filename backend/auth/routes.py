"""FastAPI Router for Authentication and Account Management."""
from fastapi import APIRouter, Depends, Request, status, Header
from sqlalchemy.orm import Session
from typing import Optional

from backend.database.session import get_db
from backend.database.models import UserModel, WalletLinkModel, KycRecordModel
from .schemas import (
    UserSignupRequest,
    UserLoginRequest,
    EmailVerificationRequest,
    ResendVerificationRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    TokenResponse,
    UserSummaryResponse,
    UserProfileResponse,
)
from .service import AuthService
from .policy import get_current_user, get_token_from_header

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/signup", response_model=dict, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignupRequest, db: Session = Depends(get_db)):
    """Register a new user account with secure password hashing."""
    user, verification_token = AuthService.signup(db, payload.email, payload.password)
    return {
        "message": "Account created successfully. Please verify your email.",
        "user_id": user.id,
        "email": user.email,
        "verification_token": verification_token,  # Provided for local dev & testing
    }


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate with email and password, returning Bearer access token."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    token, expires_in, user = AuthService.login(db, payload.email, payload.password, client_ip)
    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=expires_in,
        user=UserSummaryResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
        ),
    )


@router.post("/verify-email")
async def verify_email(payload: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Verify email address using a single-use token."""
    user = AuthService.verify_email(db, payload.token)
    return {
        "message": "Email verified successfully.",
        "email": user.email,
        "is_verified": user.is_verified,
    }


@router.post("/forgot-password")
async def forgot_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Initiate password recovery."""
    reset_token = AuthService.request_password_reset(db, payload.email)
    return {
        "message": "If that email exists in our system, recovery instructions have been sent.",
        "reset_token": reset_token,  # Provided for deterministic testing in dev
    }


@router.post("/reset-password")
async def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Set new password using single-use reset token."""
    user = AuthService.reset_password(db, payload.token, payload.new_password)
    return {
        "message": "Password updated successfully. You may now sign in with your new password.",
        "email": user.email,
    }


@router.post("/logout")
async def logout(
    token: Optional[str] = Depends(get_token_from_header),
    db: Session = Depends(get_db)
):
    """Revoke active JWT access token to invalidate current session."""
    if token:
        AuthService.logout(db, token)
    return {"message": "Logged out successfully. Session token revoked."}


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve authenticated user's profile, linked wallets summary, and KYC status."""
    wallets = db.query(WalletLinkModel).filter(WalletLinkModel.user_id == current_user.id).all()
    kyc = db.query(KycRecordModel).filter(KycRecordModel.user_id == current_user.id).first()

    payment_wallet = next((w.address for w in wallets if w.role == "payment" and w.is_primary), None)
    if not payment_wallet and wallets:
        payment_wallet = next((w.address for w in wallets if w.role == "payment"), None)

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        linked_wallets_count=len(wallets),
        active_payment_wallet=payment_wallet,
        kyc_status=kyc.status if kyc else "NOT_STARTED",
        is_kyc_simulated=kyc.is_simulated if kyc else True,
    )
