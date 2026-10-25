"""Administrative user lifecycle management API endpoints (Module 12).

Adheres to Module 12 security requirements:
- Strictly restricted to administrators (require_admin_user).
- Passwords are automatically hashed with Argon2id; never stored in plaintext.
- Prevents accidental lockout of the last active administrator.
- Validates inputs and returns safe UserResponse schemas without password hashes.
"""

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import hash_password
from app.core.user_auth import require_admin_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import (
    count_active_admins,
    count_users,
    create_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    update_user,
)
from app.schemas.auth import (
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserRoleType,
    UserUpdateRequest,
)
from app.schemas.common import ErrorResponse
from app.schemas.device import PaginationMeta

router = APIRouter()


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user accounts",
    description="Lists registered users with pagination. Accessible only by administrators.",
    responses={
        status.HTTP_200_OK: {"model": UserListResponse, "description": "Paginated list of users."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Authentication required."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Administrator privilege required."},
    },
)
def get_users_endpoint(
    role: UserRoleType | None = Query(default=None, description="Filter by user role."),
    is_active: bool | None = Query(default=None, description="Filter by active status."),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    _admin: User = Depends(require_admin_user),
    session: Session = Depends(get_db),
) -> UserListResponse:
    """List users with pagination."""
    users = list_users(
        session=session,
        role=role,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    total = count_users(
        session=session,
        role=role,
        is_active=is_active,
    )
    items = [UserResponse.model_validate(u) for u in users]
    has_more = (offset + limit) < total

    return UserListResponse(
        data=items,
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        ),
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision new user account",
    description="Provisions a new user account with hashed credentials. Accessible only by administrators.",
    responses={
        status.HTTP_201_CREATED: {"model": UserResponse, "description": "User created successfully."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Authentication required."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Administrator privilege required."},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Email address already registered."},
    },
)
def create_user_endpoint(
    payload: UserCreateRequest,
    _admin: User = Depends(require_admin_user),
    session: Session = Depends(get_db),
) -> UserResponse:
    """Create a new user."""
    existing = get_user_by_email(session, payload.email)
    if existing is not None:
        raise ConflictException("A user with this email address already exists.")

    hashed = hash_password(payload.password)
    new_user = create_user(
        session=session,
        email=payload.email,
        password_hash=hashed,
        display_name=payload.display_name,
        role=payload.role,
        is_active=payload.is_active,
    )
    session.commit()
    return UserResponse.model_validate(new_user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user account",
    description="Updates role, active status, display name, or password. Accessible only by administrators.",
    responses={
        status.HTTP_200_OK: {"model": UserResponse, "description": "User updated successfully."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Authentication required."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Administrator privilege required."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "User not found."},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Cannot deactivate or demote last admin."},
    },
)
def update_user_endpoint(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    current_admin: User = Depends(require_admin_user),
    session: Session = Depends(get_db),
) -> UserResponse:
    """Update user account settings."""
    target_user = get_user_by_id(session, user_id)
    if target_user is None:
        raise NotFoundException("User not found.")

    # Guard against self-deactivation or demotion of the last active administrator
    if target_user.id == current_admin.id:
        if payload.is_active is False:
            raise ConflictException("Administrators cannot deactivate their own account.")
        if payload.role is not None and payload.role != "admin":
            active_admins = count_active_admins(session)
            if active_admins <= 1:
                raise ConflictException("Cannot demote the sole active administrator account.")

    new_hash: str | None = None
    if payload.password is not None:
        new_hash = hash_password(payload.password)

    updated = update_user(
        session=session,
        user=target_user,
        display_name=payload.display_name,
        role=payload.role,
        is_active=payload.is_active,
        password_hash=new_hash,
    )
    session.commit()
    return UserResponse.model_validate(updated)
