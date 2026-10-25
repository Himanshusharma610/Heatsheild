"""User persistence repository for authentication and account management (Module 12)."""

import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_id(session: Session, user_id: uuid.UUID) -> User | None:
    """Retrieve user entity by primary key UUID."""
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    """Retrieve user entity by unique email address (case-insensitive)."""
    stmt = select(User).where(func.lower(User.email) == email.strip().lower())
    return session.scalars(stmt).first()


def list_users(
    session: Session,
    role: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    """Retrieve paginated user records with optional filtering."""
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(stmt).all())


def count_users(
    session: Session,
    role: str | None = None,
    is_active: bool | None = None,
) -> int:
    """Count user records matching criteria."""
    stmt = select(func.count(User.id))
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    return session.scalar(stmt) or 0


def count_active_admins(session: Session) -> int:
    """Count the number of active administrators to prevent lockout."""
    stmt = select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True))
    return session.scalar(stmt) or 0


def create_user(
    session: Session,
    email: str,
    password_hash: str,
    display_name: str | None = None,
    role: str = "viewer",
    is_active: bool = True,
) -> User:
    """Create and persist a new user entity."""
    user = User(
        email=email.strip().lower(),
        password_hash=password_hash,
        display_name=display_name.strip() if display_name else None,
        role=role,
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user


def update_user(
    session: Session,
    user: User,
    display_name: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    password_hash: str | None = None,
) -> User:
    """Update fields on an existing user entity."""
    if display_name is not None:
        user.display_name = display_name.strip() if display_name else None
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    if password_hash is not None:
        user.password_hash = password_hash

    session.flush()
    return user
