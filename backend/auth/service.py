"""Authentication Service for User Registration, Login, Token Management, and Recovery."""
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from backend.database.models import (
    UserModel,
    EmailVerificationTokenModel,
    PasswordResetTokenModel,
    RevokedTokenModel,
    WalletLinkModel,
    KycRecordModel,
)
from backend.shared.errors import (
    AuthenticationFailedError,
    TokenRevokedOrExpiredError,
    AgentEconomyBaseException,
)
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    check_login_rate_limit,
    record_failed_login,
    clear_failed_logins,
)


class AuthService:
    """Handles core user authentication, token issuance, and account lifecycle."""

    @staticmethod
    def signup(db: Session, email: str, password: str) -> Tuple[UserModel, str]:
        """Register a new user account with secure password hashing and generate email verification token."""
        normalized_email = email.strip().lower()
        existing = db.query(UserModel).filter(UserModel.email == normalized_email).first()
        if existing:
            raise AgentEconomyBaseException(
                "An account with this email address already exists.",
                error_code="ACCOUNT_ALREADY_EXISTS"
            )

        hashed = hash_password(password)
        user_id = f"usr_{uuid.uuid4().hex[:12]}"

        user = UserModel(
            id=user_id,
            email=normalized_email,
            password_hash=hashed,
            role="user",
            is_active=True,
            is_verified=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(user)

        # Generate single-use verification token valid for 24 hours
        token_str = secrets.token_urlsafe(32)
        verification_token = EmailVerificationTokenModel(
            token=token_str,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            used=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(verification_token)

        # Initialize default KYC record with NOT_STARTED
        kyc = KycRecordModel(
            user_id=user_id,
            status="NOT_STARTED",
            provider="mock_simulated",
            is_simulated=True,
            simulation_disclaimer="SIMULATED - NOT REAL-WORLD IDENTITY VERIFICATION",
            created_at=datetime.now(timezone.utc),
        )
        db.add(kyc)

        db.commit()
        db.refresh(user)
        return user, token_str

    @staticmethod
    def login(db: Session, email: str, password: str, client_ip: str = "127.0.0.1") -> Tuple[str, int, UserModel]:
        """Authenticate user with rate limiting and secure password check.
        Uses generic error message to prevent account enumeration.
        """
        normalized_email = email.strip().lower()
        rate_key = f"{client_ip}:{normalized_email}"

        if not check_login_rate_limit(rate_key):
            raise AgentEconomyBaseException(
                "Too many failed login attempts. Please try again in 15 minutes.",
                error_code="LOGIN_RATE_LIMITED"
            )

        user = db.query(UserModel).filter(UserModel.email == normalized_email).first()
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            record_failed_login(rate_key)
            raise AuthenticationFailedError("Invalid email or password.")

        clear_failed_logins(rate_key)
        token, jti, expires_in = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role
        )
        return token, expires_in, user

    @staticmethod
    def verify_email(db: Session, token: str) -> UserModel:
        """Validate and consume email verification token."""
        record = db.query(EmailVerificationTokenModel).filter(
            EmailVerificationTokenModel.token == token,
            EmailVerificationTokenModel.used == False
        ).first()

        if not record:
            raise AgentEconomyBaseException(
                "Invalid or expired verification token.",
                error_code="INVALID_VERIFICATION_TOKEN"
            )

        now = datetime.now(timezone.utc)
        record_exp = record.expires_at
        if record_exp.tzinfo is None:
            record_exp = record_exp.replace(tzinfo=timezone.utc)

        if record_exp < now:
            raise AgentEconomyBaseException(
                "Verification token has expired.",
                error_code="VERIFICATION_TOKEN_EXPIRED"
            )

        record.used = True
        user = db.query(UserModel).filter(UserModel.id == record.user_id).first()
        if not user:
            raise AgentEconomyBaseException("User not found.", error_code="USER_NOT_FOUND")

        user.is_verified = True
        user.updated_at = now
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def request_password_reset(db: Session, email: str) -> Optional[str]:
        """Generate single-use password reset token (1 hour TTL)."""
        normalized_email = email.strip().lower()
        user = db.query(UserModel).filter(UserModel.email == normalized_email).first()
        if not user or not user.is_active:
            # Safe return without disclosing email presence
            return None

        token_str = secrets.token_urlsafe(32)
        reset_record = PasswordResetTokenModel(
            token=token_str,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(reset_record)
        db.commit()
        return token_str

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> UserModel:
        """Verify reset token and update password securely."""
        record = db.query(PasswordResetTokenModel).filter(
            PasswordResetTokenModel.token == token,
            PasswordResetTokenModel.used == False
        ).first()

        if not record:
            raise AgentEconomyBaseException(
                "Invalid or expired password reset token.",
                error_code="INVALID_RESET_TOKEN"
            )

        now = datetime.now(timezone.utc)
        record_exp = record.expires_at
        if record_exp.tzinfo is None:
            record_exp = record_exp.replace(tzinfo=timezone.utc)

        if record_exp < now:
            raise AgentEconomyBaseException(
                "Password reset token has expired.",
                error_code="RESET_TOKEN_EXPIRED"
            )

        record.used = True
        user = db.query(UserModel).filter(UserModel.id == record.user_id).first()
        if not user:
            raise AgentEconomyBaseException("User not found.", error_code="USER_NOT_FOUND")

        user.password_hash = hash_password(new_password)
        user.updated_at = now
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def logout(db: Session, token: str) -> bool:
        """Revoke the current access token by recording its jti in the blacklist."""
        try:
            payload = decode_access_token(token)
            jti = payload.get("jti")
            user_id = payload.get("sub")
            exp = payload.get("exp")
            if jti and user_id and exp:
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                revoked = RevokedTokenModel(
                    jti=jti,
                    user_id=user_id,
                    revoked_at=datetime.now(timezone.utc),
                    expires_at=expires_at,
                )
                db.add(revoked)
                db.commit()
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def is_token_revoked(db: Session, jti: str) -> bool:
        """Check if token jti is present in revocation blacklist."""
        return db.query(RevokedTokenModel).filter(RevokedTokenModel.jti == jti).first() is not None
