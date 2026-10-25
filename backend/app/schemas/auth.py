"""Pydantic schemas for human user authentication and account lifecycle (Module 12)."""

from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.device import PaginationMeta

UserRoleType = Literal["viewer", "supervisor", "admin"]


class LoginRequest(BaseModel):
    """Credentials payload for human user login."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(description="Registered user email address.")
    password: str = Field(min_length=1, max_length=128, description="User password.")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class UserResponse(BaseModel):
    """Public user profile data. Never exposes password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique user identifier.")
    email: str = Field(description="User email address.")
    display_name: str | None = Field(default=None, description="Human-friendly name.")
    role: UserRoleType = Field(description="Assigned role ('viewer', 'supervisor', 'admin').")
    is_active: bool = Field(description="Active account status.")
    created_at: datetime = Field(description="Account creation timestamp (UTC).")


class LoginResponse(BaseModel):
    """Authentication success payload containing JWT access token and user profile."""

    model_config = ConfigDict(extra="forbid")

    access_token: str = Field(description="Signed JWT access token.")
    token_type: str = Field(default="bearer", description="Token type, always 'bearer'.")
    expires_in: int = Field(description="Token lifetime in seconds.")
    user: UserResponse = Field(description="Authenticated user profile.")


class UserCreateRequest(BaseModel):
    """Administrator payload to provision a new user account."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(description="Unique email address for the user.")
    password: str = Field(min_length=8, max_length=128, description="Initial password (min 8 chars).")
    display_name: str | None = Field(default=None, max_length=200, description="Display name.")
    role: UserRoleType = Field(default="viewer", description="Role to assign.")
    is_active: bool = Field(default=True, description="Initial active status.")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class UserUpdateRequest(BaseModel):
    """Administrator payload to update an existing user account."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=200, description="Updated display name.")
    role: UserRoleType | None = Field(default=None, description="Updated role.")
    is_active: bool | None = Field(default=None, description="Updated active status.")
    password: str | None = Field(default=None, min_length=8, max_length=128, description="Reset password.")


class UserListResponse(BaseModel):
    """Paginated list of user accounts for admin management."""

    model_config = ConfigDict(extra="forbid")

    data: list[UserResponse] = Field(description="List of user profiles.")
    pagination: PaginationMeta = Field(description="Pagination metadata.")


class LogoutResponse(BaseModel):
    """Logout confirmation response."""

    message: str = Field(default="Logged out successfully.")
