"""Sensor reading repository operations."""

from datetime import datetime
from decimal import Decimal
from typing import Any
import uuid
from sqlalchemy import case, func, select
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
    device_id: uuid.UUID | None = None,
    worksite_id: uuid.UUID | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    quality_status: str | None = None,
    order_asc: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> list[tuple[SensorReading, str]]:
    """Query time-range history with deterministic ordering and device metadata."""
    from app.models.device import Device

    time_col = func.coalesce(SensorReading.measured_at, SensorReading.received_at)
    stmt = (
        select(SensorReading, Device.device_code)
        .join(Device, SensorReading.device_id == Device.id)
    )
    if device_id is not None:
        stmt = stmt.where(SensorReading.device_id == device_id)
    if worksite_id is not None:
        stmt = stmt.where(Device.worksite_id == worksite_id)
    if start_time is not None:
        stmt = stmt.where(time_col >= start_time)
    if end_time is not None:
        stmt = stmt.where(time_col <= end_time)
    if quality_status is not None:
        stmt = stmt.where(SensorReading.quality_status == quality_status)

    if order_asc:
        stmt = stmt.order_by(time_col.asc(), SensorReading.id.asc())
    else:
        stmt = stmt.order_by(time_col.desc(), SensorReading.id.desc())

    stmt = stmt.limit(limit).offset(offset)
    res = session.execute(stmt).all()
    return [(row[0], row[1]) for row in res]


def count_reading_history(
    session: Session,
    device_id: uuid.UUID | None = None,
    worksite_id: uuid.UUID | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    quality_status: str | None = None,
) -> int:
    """Count total historical readings matching query filters."""
    from app.models.device import Device

    time_col = func.coalesce(SensorReading.measured_at, SensorReading.received_at)
    stmt = select(func.count(SensorReading.id)).select_from(SensorReading)
    if worksite_id is not None:
        stmt = stmt.join(Device, SensorReading.device_id == Device.id).where(Device.worksite_id == worksite_id)
    if device_id is not None:
        stmt = stmt.where(SensorReading.device_id == device_id)
    if start_time is not None:
        stmt = stmt.where(time_col >= start_time)
    if end_time is not None:
        stmt = stmt.where(time_col <= end_time)
    if quality_status is not None:
        stmt = stmt.where(SensorReading.quality_status == quality_status)

    return session.scalar(stmt) or 0


def get_reading_summary(
    session: Session,
    device_id: uuid.UUID | None = None,
    worksite_id: uuid.UUID | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    quality_status: str | None = None,
) -> dict[str, Any]:
    """Compute transparent descriptive statistics using SQL aggregations.

    Calculates min/max/mean for valid measurements, and counts of
    valid/invalid/suspect/missing readings. Excludes invalid readings from numerical averages.
    """
    from app.models.device import Device
    from app.services.heat_index import calculate_heat_index

    time_col = func.coalesce(SensorReading.measured_at, SensorReading.received_at)

    is_valid_temp = (SensorReading.quality_status == "valid") & (SensorReading.temperature_c.is_not(None))
    is_valid_hum = (SensorReading.quality_status == "valid") & (SensorReading.relative_humidity_pct.is_not(None))

    stmt = select(
        func.count(SensorReading.id).label("total_count"),
        func.count(case((SensorReading.quality_status == "valid", 1))).label("valid_count"),
        func.count(case((SensorReading.quality_status == "invalid", 1))).label("invalid_count"),
        func.count(case((SensorReading.quality_status == "suspect", 1))).label("suspect_count"),
        func.count(case((SensorReading.quality_status == "missing", 1))).label("missing_count"),
        func.min(case((is_valid_temp, SensorReading.temperature_c))).label("min_temp"),
        func.max(case((is_valid_temp, SensorReading.temperature_c))).label("max_temp"),
        func.avg(case((is_valid_temp, SensorReading.temperature_c))).label("avg_temp"),
        func.min(case((is_valid_hum, SensorReading.relative_humidity_pct))).label("min_hum"),
        func.max(case((is_valid_hum, SensorReading.relative_humidity_pct))).label("max_hum"),
        func.avg(case((is_valid_hum, SensorReading.relative_humidity_pct))).label("avg_hum"),
    ).select_from(SensorReading)

    if worksite_id is not None:
        stmt = stmt.join(Device, SensorReading.device_id == Device.id).where(Device.worksite_id == worksite_id)
    if device_id is not None:
        stmt = stmt.where(SensorReading.device_id == device_id)
    if start_time is not None:
        stmt = stmt.where(time_col >= start_time)
    if end_time is not None:
        stmt = stmt.where(time_col <= end_time)
    if quality_status is not None:
        stmt = stmt.where(SensorReading.quality_status == quality_status)

    row = session.execute(stmt).one()

    # Query valid readings to compute heat index min, max, mean deterministically
    hi_min: float | None = None
    hi_max: float | None = None
    hi_mean: float | None = None

    if row.valid_count > 0:
        # Compute heat index on valid temperature & humidity pairs
        hi_stmt = select(SensorReading.temperature_c, SensorReading.relative_humidity_pct).where(
            SensorReading.quality_status == "valid",
            SensorReading.temperature_c.is_not(None),
            SensorReading.relative_humidity_pct.is_not(None),
        )
        if worksite_id is not None:
            hi_stmt = hi_stmt.join(Device, SensorReading.device_id == Device.id).where(Device.worksite_id == worksite_id)
        if device_id is not None:
            hi_stmt = hi_stmt.where(SensorReading.device_id == device_id)
        if start_time is not None:
            hi_stmt = hi_stmt.where(time_col >= start_time)
        if end_time is not None:
            hi_stmt = hi_stmt.where(time_col <= end_time)

        valid_pairs = session.execute(hi_stmt).all()
        hi_values: list[float] = []
        for t, h in valid_pairs:
            res = calculate_heat_index(float(t), float(h), quality_status="valid")
            if res.status == "valid" and res.value_c is not None:
                hi_values.append(res.value_c)

        if hi_values:
            hi_min = round(min(hi_values), 2)
            hi_max = round(max(hi_values), 2)
            hi_mean = round(sum(hi_values) / len(hi_values), 2)

    return {
        "start_time": start_time,
        "end_time": end_time,
        "total_readings": row.total_count or 0,
        "valid_readings": row.valid_count or 0,
        "invalid_readings": row.invalid_count or 0,
        "suspect_readings": row.suspect_count or 0,
        "missing_readings": row.missing_count or 0,
        "temperature_c": {
            "min": round(float(row.min_temp), 2) if row.min_temp is not None else None,
            "max": round(float(row.max_temp), 2) if row.max_temp is not None else None,
            "mean": round(float(row.avg_temp), 2) if row.avg_temp is not None else None,
        },
        "relative_humidity_pct": {
            "min": round(float(row.min_hum), 2) if row.min_hum is not None else None,
            "max": round(float(row.max_hum), 2) if row.max_hum is not None else None,
            "mean": round(float(row.avg_hum), 2) if row.avg_hum is not None else None,
        },
        "heat_index_c": {
            "min": hi_min,
            "max": hi_max,
            "mean": hi_mean,
        },
    }


def get_latest_readings(
    session: Session,
    device_id: uuid.UUID | None = None,
    worksite_id: uuid.UUID | None = None,
    quality_status: str | None = None,
    limit: int = 50,
) -> list[tuple[SensorReading, str]]:
    """Retrieve the most recent reading for each device or a single device.

    Returns a list of tuples: (reading, device_code).
    """
    from app.models.device import Device

    if device_id is not None:
        stmt = (
            select(SensorReading, Device.device_code)
            .join(Device, SensorReading.device_id == Device.id)
            .where(SensorReading.device_id == device_id)
        )
        if quality_status is not None:
            stmt = stmt.where(SensorReading.quality_status == quality_status)
        stmt = stmt.order_by(SensorReading.received_at.desc(), SensorReading.measured_at.desc()).limit(1)
        res = session.execute(stmt).all()
        return [(row[0], row[1]) for row in res]

    # Query matching devices and retrieve the latest reading for each
    dev_stmt = select(Device)
    if worksite_id is not None:
        dev_stmt = dev_stmt.where(Device.worksite_id == worksite_id)
    devices = list(session.scalars(dev_stmt).all())

    results: list[tuple[SensorReading, str]] = []
    for dev in devices[:limit]:
        r_stmt = select(SensorReading).where(SensorReading.device_id == dev.id)
        if quality_status is not None:
            r_stmt = r_stmt.where(SensorReading.quality_status == quality_status)
        r_stmt = r_stmt.order_by(SensorReading.received_at.desc(), SensorReading.measured_at.desc()).limit(1)
        latest = session.scalars(r_stmt).first()
        if latest is not None:
            results.append((latest, dev.device_code))

    return results
