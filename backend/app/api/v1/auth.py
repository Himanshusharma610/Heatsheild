"""Human authentication endpoints for login, profile inspection, and session termination (Module 12).

Adheres to Module 12 security requirements:
- Generic failure messages: Does not disclose whether email exists or not.
- Constant-time verification with Argon2id password hashes.
- Never logs passwords, tokens, or hashes.
- Rejects deactivated accounts.
- Issues standard Bearer JWT tokens.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, verify_password
from app.core.user_auth import require_authenticated_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import get_user_by_email
from app.schemas.auth import LoginRequest, LoginResponse, LogoutResponse, UserResponse
from app.schemas.common import ErrorResponse

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate human user",
    description=(
        "Authenticates a dashboard user (viewer, supervisor, admin) with email and password. "
        "Returns a signed JWT Bearer access token. Generic failure responses prevent account enumeration."
    ),
    responses={
        status.HTTP_200_OK: {"model": LoginResponse, "description": "Authentication successful."},
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Invalid credentials or deactivated account.",
        },
    },
)
def login_endpoint(
    payload: LoginRequest,
    session: Session = Depends(get_db),
) -> LoginResponse:
    """Validate credentials and issue JWT access token."""
    user = get_user_by_email(session, payload.email)

    # Use generic message for either user missing or password mismatch to prevent enumeration
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedException("Invalid email or password.")

    if not user.is_active:
        raise UnauthorizedException("Account is deactivated. Contact an administrator.")

    token, expires_in = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Current authenticated user profile",
    description="Returns public identity and role permissions for the currently authenticated user session.",
    responses={
        status.HTTP_200_OK: {"model": UserResponse, "description": "Current user profile."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Authentication required."},
    },
)
def get_current_user_profile(
    user: User = Depends(require_authenticated_user),
) -> UserResponse:
    """Retrieve current user profile."""
    return UserResponse.model_validate(user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Terminate user session",
    description="Statelessly acknowledges user logout. The client must discard the stored JWT access token.",
    responses={
        status.HTTP_200_OK: {"model": LogoutResponse, "description": "Session terminated."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Authentication required."},
    },
)
def logout_endpoint(
    _user: User = Depends(require_authenticated_user),
) -> LogoutResponse:
    """Acknowledge session invalidation."""
    return LogoutResponse(message="Logged out successfully.")
