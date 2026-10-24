"""Device authentication dependency and verification utilities.

Protects IoT telemetry ingestion endpoints using per-device pre-shared key hashes.
Adheres to Module 6 security constraints:
- Uses constant-time comparison to prevent timing side-channel attacks.
- Returns generic 401 error envelopes without disclosing device existence or registration state.
- Never logs raw tokens, Authorization headers, or X-Device-Token values.
- Separates device authentication from human user / supervisor authentication.
"""

import hashlib
import logging
import secrets
from fastapi import Header
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException
from app.models.device import Device
from app.repositories.device import get_device_by_code, hash_device_token

logger = logging.getLogger(__name__)

# Precomputed dummy hash for constant-time comparison when a device is absent or lacks a key
DUMMY_HASH = hashlib.sha256(b"heatshield-bharat-dummy-timing-mitigation").hexdigest()


def extract_device_token(
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
    authorization: str | None = Header(default=None),
) -> str:
    """Extract device token from X-Device-Token header or Authorization: Bearer scheme."""
    if x_device_token and x_device_token.strip():
        return x_device_token.strip()

    if authorization and authorization.strip().lower().startswith("bearer "):
        token = authorization.strip()[7:].strip()
        if token:
            return token

    raise UnauthorizedException("Device authentication required")


def authenticate_device(
    session: Session,
    device_code: str,
    raw_token: str,
) -> Device:
    """Validate device credentials in constant time against stored SHA-256 hash.

    Args:
        session: Active database session.
        device_code: Stable device code from payload.
        raw_token: Presented authentication token from request header.

    Returns:
        The authenticated Device model instance.

    Raises:
        UnauthorizedException: If device is not found, inactive, lacks a key,
            or presents an invalid token.
    """
    token_hash = hash_device_token(raw_token)
    device = get_device_by_code(session, device_code)

    if device is None or not device.is_active or not device.api_key_hash:
        # Perform dummy comparison to equalize execution timing
        secrets.compare_digest(token_hash, DUMMY_HASH)
        raise UnauthorizedException("Invalid device credentials")

    # Constant-time comparison against the stored hash
    is_valid = secrets.compare_digest(token_hash, device.api_key_hash)
    if not is_valid:
        raise UnauthorizedException("Invalid device credentials")

    return device
