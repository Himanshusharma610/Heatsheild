"""Device repository operations."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device import Device


def register_device(
    session: Session,
    device_code: str,
    worksite_id: uuid.UUID,
    display_name: str | None = None,
    firmware_version: str | None = None,
) -> Device:
    """Register a new device node assigned to a worksite."""
    device = Device(
        device_code=device_code,
        worksite_id=worksite_id,
        display_name=display_name,
        firmware_version=firmware_version,
        status="registered",
        is_active=True,
    )
    session.add(device)
    session.flush()
    return device


def get_device_by_id(session: Session, device_id: uuid.UUID) -> Device | None:
    """Retrieve device by primary key."""
    return session.get(Device, device_id)


def get_device_by_code(session: Session, device_code: str) -> Device | None:
    """Retrieve device by stable device code."""
    stmt = select(Device).where(Device.device_code == device_code)
    return session.scalars(stmt).first()


def list_devices_by_worksite(
    session: Session,
    worksite_id: uuid.UUID,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> list[Device]:
    """List devices assigned to a worksite with optional active filtering."""
    stmt = select(Device).where(Device.worksite_id == worksite_id)
    if active_only:
        stmt = stmt.where(Device.is_active.is_(True))
    stmt = stmt.order_by(Device.device_code.asc()).limit(limit).offset(offset)
    return list(session.scalars(stmt).all())


def update_device_heartbeat(
    session: Session,
    device_id: uuid.UUID,
    seen_at: datetime | None = None,
    firmware_version: str | None = None,
) -> Device | None:
    """Update last_seen_at timestamp and set device status to online."""
    device = session.get(Device, device_id)
    if device:
        device.last_seen_at = seen_at or datetime.now(timezone.utc)
        device.status = "online"
        if firmware_version:
            device.firmware_version = firmware_version
        session.flush()
    return device


def deactivate_device(session: Session, device_id: uuid.UUID) -> Device | None:
    """Soft-deactivate a device (retaining all historical readings and alerts)."""
    device = session.get(Device, device_id)
    if device:
        device.is_active = False
        device.status = "deactivated"
        session.flush()
    return device
