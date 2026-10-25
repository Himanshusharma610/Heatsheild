"""Cryptographic security utilities for password hashing and JWT access tokens (Module 12).

Adheres to Module 12 requirements:
- Password hashing using Argon2id with OWASP recommended parameters.
- Never stores or logs plaintext passwords.
- Secure JWT generation and signature verification using HMAC-SHA256 (HS256).
- Explicit token expiration and type validation.
- Safe error handling that does not leak cryptographic internals.
"""

from datetime import datetime, timedelta, timezone
import logging
import uuid
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
import jwt

from app.config import get_settings
from app.core.exceptions import UnauthorizedException

logger = logging.getLogger(__name__)

# Argon2id password hasher with OWASP recommended parameters
# Memory: 64 MiB (65536 KiB), Time: 3 iterations, Parallelism: 4 threads
_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id.

    Args:
        plain_password: The raw password string supplied by user.

    Returns:
        The Argon2id hash string (e.g. $argon2id$v=19$m=65536,t=3,p=4$...).
    """
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash.

    Args:
        plain_password: The plaintext password candidate.
        hashed_password: The stored Argon2id hash string.

    Returns:
        True if the password matches, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception as exc:
        logger.error("Unexpected error during password verification: %s", type(exc).__name__)
        return False


def create_access_token(
    user_id: uuid.UUID | str,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    """Generate a signed JWT access token for an authenticated user.

    Args:
        user_id: The unique UUID of the user.
        email: The verified email address of the user.
        role: The assigned role ('admin', 'supervisor', 'viewer').
        expires_delta: Optional custom duration; defaults to settings.AUTH_TOKEN_EXPIRE_MINUTES.

    Returns:
        A tuple of (encoded_jwt_str, expires_in_seconds).
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
        expires_in = int(expires_delta.total_seconds())
    else:
        expire = now + timedelta(minutes=settings.AUTH_TOKEN_EXPIRE_MINUTES)
        expires_in = settings.AUTH_TOKEN_EXPIRE_MINUTES * 60

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    secret = settings.SECRET_KEY.get_secret_value()
    token = jwt.encode(payload, secret, algorithm=settings.AUTH_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Args:
        token: The raw Bearer token string.

    Returns:
        The decoded payload dictionary containing sub, email, role, etc.

    Raises:
        UnauthorizedException: If token is expired, malformed, or signature is invalid.
    """
    settings = get_settings()
    secret = settings.SECRET_KEY.get_secret_value()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.AUTH_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type.")
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Authentication token has expired.")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Invalid authentication token.")
