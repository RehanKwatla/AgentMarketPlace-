"""Security, Password Hashing, JWT Tokens, and Throttling for DI-06."""
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
import bcrypt
import jwt

from backend.shared.config import get_settings
from backend.shared.errors import (
    AuthenticationFailedError,
    TokenRevokedOrExpiredError,
)

settings = get_settings()

# In-memory rate limiting tracker: key -> list of failure timestamps
_failed_attempts: Dict[str, list[float]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 900  # 15 minutes


def hash_password(password: str) -> str:
    """Securely hash a password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(
    user_id: str,
    email: str,
    role: str = "user",
    expires_minutes: Optional[int] = None
) -> Tuple[str, str, int]:
    """Create a signed JWT token with jti (unique ID for revocation).
    Returns (token_string, jti, expires_in_seconds).
    """
    ttl = expires_minutes or settings.auth_access_token_expire_minutes
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ttl)
    jti = str(uuid.uuid4())

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(
        payload,
        settings.auth_jwt_secret,
        algorithm=settings.auth_jwt_algorithm
    )
    expires_in_seconds = ttl * 60
    return token, jti, expires_in_seconds


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token signature and expiration."""
    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=[settings.auth_jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenRevokedOrExpiredError("Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise AuthenticationFailedError("Invalid authentication token.")


# Rate limiting / Login throttling
def check_login_rate_limit(key: str) -> bool:
    """Returns True if within rate limit, False if throttled."""
    now = time.time()
    cutoff = now - LOCKOUT_WINDOW_SECONDS
    attempts = [t for t in _failed_attempts.get(key, []) if t > cutoff]
    _failed_attempts[key] = attempts
    return len(attempts) < MAX_FAILED_ATTEMPTS


def record_failed_login(key: str) -> None:
    """Record a failed login attempt for rate limiting."""
    now = time.time()
    if key not in _failed_attempts:
        _failed_attempts[key] = []
    _failed_attempts[key].append(now)


def clear_failed_logins(key: str) -> None:
    """Reset failed login count upon successful sign-in."""
    _failed_attempts.pop(key, None)
