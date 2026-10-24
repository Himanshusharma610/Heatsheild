"""Sensor reading repository operations."""

from datetime import datetime
from decimal import Decimal
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reading import SensorReading


def create_reading(
    session: Session,
    device_id: uuid.UUID,
    event_id: str,
    measured_at: datetime | None = None,
    received_at: datetime | None = None,
    temperature_c: Decimal | float | None = None,
    relative_humidity_pct: Decimal | float | None = None,
    quality_status: str = "valid",
    source_mode: str = "hardware",
    firmware_version: str | None = None,
) -> SensorReading:
    """Persist an environmental sensor reading."""
    temp_decimal = Decimal(str(temperature_c)) if temperature_c is not None else None
    hum_decimal = Decimal(str(relative_humidity_pct)) if relative_humidity_pct is not None else None

    params: dict[str, Any] = {
        "device_id": device_id,
        "event_id": event_id,
        "measured_at": measured_at,
        "temperature_c": temp_decimal,
        "relative_humidity_pct": hum_decimal,
        "quality_status": quality_status,
        "source_mode": source_mode,
        "firmware_version": firmware_version,
    }
    if received_at is not None:
        params["received_at"] = received_at

    reading = SensorReading(**params)
    session.add(reading)
    session.flush()
    return reading


def get_reading_by_id(session: Session, reading_id: uuid.UUID) -> SensorReading | None:
    """Retrieve reading by primary key."""
    return session.get(SensorReading, reading_id)


def get_reading_by_device_and_event(
    session: Session,
    device_id: uuid.UUID,
    event_id: str,
) -> SensorReading | None:
    """Lookup reading by device ID and event ID for deduplication checks."""
    stmt = select(SensorReading).where(
        SensorReading.device_id == device_id,
        SensorReading.event_id == event_id,
    )
    return session.scalars(stmt).first()


def get_latest_valid_reading(session: Session, device_id: uuid.UUID) -> SensorReading | None:
    """Retrieve the most recently received valid reading for a device."""
    stmt = (
        select(SensorReading)
        .where(
            SensorReading.device_id == device_id,
            SensorReading.quality_status == "valid",
        )
        .order_by(SensorReading.received_at.desc(), SensorReading.measured_at.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def get_reading_history(
    session: Session,
    device_id: uuid.UUID,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    quality_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SensorReading]:
    """Query time-range history for a device ordered by received and measured timestamp descending."""
    stmt = select(SensorReading).where(SensorReading.device_id == device_id)

    if start_time is not None:
        stmt = stmt.where(SensorReading.received_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(SensorReading.received_at <= end_time)
    if quality_status is not None:
        stmt = stmt.where(SensorReading.quality_status == quality_status)

    stmt = stmt.order_by(SensorReading.received_at.desc(), SensorReading.measured_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(stmt).all())
