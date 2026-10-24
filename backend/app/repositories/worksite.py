"""Worksite repository operations."""

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.worksite import Worksite


def create_worksite(
    session: Session,
    name: str,
    location_description: str | None = None,
) -> Worksite:
    """Create and persist a new worksite."""
    worksite = Worksite(
        name=name,
        location_description=location_description,
        is_active=True,
    )
    session.add(worksite)
    session.flush()
    return worksite


def get_worksite_by_id(session: Session, worksite_id: uuid.UUID) -> Worksite | None:
    """Retrieve worksite by primary key."""
    return session.get(Worksite, worksite_id)


def get_worksite_by_name(session: Session, name: str) -> Worksite | None:
    """Retrieve worksite by name."""
    stmt = select(Worksite).where(Worksite.name == name)
    return session.scalars(stmt).first()


def list_active_worksites(session: Session, limit: int = 50, offset: int = 0) -> list[Worksite]:
    """List active worksites with pagination."""
    stmt = (
        select(Worksite)
        .where(Worksite.is_active.is_(True))
        .order_by(Worksite.name.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt).all())


def deactivate_worksite(session: Session, worksite_id: uuid.UUID) -> Worksite | None:
    """Soft-deactivate a worksite (historical preservation)."""
    worksite = session.get(Worksite, worksite_id)
    if worksite:
        worksite.is_active = False
        session.flush()
    return worksite
