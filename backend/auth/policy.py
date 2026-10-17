"""Access Policy Dependencies and Role-Based Authorization for FastAPI."""
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.database.models import UserModel, KycRecordModel, WalletLinkModel
from backend.shared.errors import (
    AuthenticationFailedError,
    TokenRevokedOrExpiredError,
    UnauthorizedAccessError,
)
from .security import decode_access_token
from .service import AuthService


def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract Bearer token from Authorization HTTP header."""
    if not authorization:
        return None
    parts = authorization.split(" ")
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(
    token: Optional[str] = Depends(get_token_from_header),
    db: Session = Depends(get_db)
) -> UserModel:
    """Validate bearer token, ensure it is not revoked, and return current user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(token)
    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not jti or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token."
        )

    if AuthService.is_token_revoked(db, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked. Please sign in again."
        )

    user = db.query(UserModel).filter(UserModel.id == user_id, UserModel.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or disabled."
        )

    return user


def get_optional_current_user(
    token: Optional[str] = Depends(get_token_from_header),
    db: Session = Depends(get_db)
) -> Optional[UserModel]:
    """Optional authentication for endpoints that allow both public and authenticated views."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        jti = payload.get("jti")
        user_id = payload.get("sub")
        if not jti or not user_id or AuthService.is_token_revoked(db, jti):
            return None
        return db.query(UserModel).filter(UserModel.id == user_id, UserModel.is_active == True).first()
    except Exception:
        return None


def require_kyc_verified(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserModel:
    """Enforce that the requesting user has completed KYC verification."""
    # Admins bypass KYC
    if user.role == "admin":
        return user

    kyc = db.query(KycRecordModel).filter(KycRecordModel.user_id == user.id).first()
    if not kyc or kyc.status != "VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KYC verification required for this operation. Current status: " + (kyc.status if kyc else "NOT_STARTED")
        )
    return user


def require_payment_wallet(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WalletLinkModel:
    """Enforce that the user has a verified payment wallet configured."""
    wallet = db.query(WalletLinkModel).filter(
        WalletLinkModel.user_id == user.id,
        WalletLinkModel.role.in_(["payment", "identity"])
    ).first()

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A verified linked EVM wallet with 'payment' role is required."
        )
    return wallet


def require_admin(
    user: UserModel = Depends(get_current_user)
) -> UserModel:
    """Enforce administrator permissions."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required."
        )
    return user
