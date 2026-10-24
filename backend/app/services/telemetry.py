"""Telemetry ingestion business logic and reliability service.

Handles:
- Data quality classification and physical plausibility checks.
- Server vs device timestamp reconciliation.
- Idempotent deduplication and conflict detection for retransmitted events.
- Atomic persistence with transactional integrity and rollback safety.
- Device heartbeat updates.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
import math
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, ServiceUnavailableException
from app.models.device import Device
from app.models.reading import SensorReading
from app.repositories.device import update_device_heartbeat
from app.repositories.reading import create_reading, get_reading_by_device_and_event
from app.schemas.reading import ReadingCreateRequest

logger = logging.getLogger(__name__)

# Max allowable device clock drift into the future before tagging suspect (10 minutes)
MAX_FUTURE_CLOCK_DRIFT = timedelta(minutes=10)
# Extreme future clock drift (24 hours) after which timestamp is deemed invalid
MAX_EXTREME_CLOCK_DRIFT = timedelta(hours=24)
# Historical threshold: timestamps before 2020 are deemed suspect (uninitialized RTC default)
EARLIEST_PLAUSIBLE_TIMESTAMP = datetime(2020, 1, 1, tzinfo=timezone.utc)

# Physical plausibility boundaries (India / outdoor thermal monitoring)
TEMP_PLAUSIBILITY_MIN = -20.0
TEMP_PLAUSIBILITY_MAX = 70.0
TEMP_EXTREME_MIN = -40.0
TEMP_EXTREME_MAX = 85.0


def assess_reading_quality(
    measured_at: datetime | None,
    received_at: datetime,
    temperature_c: float | None,
    relative_humidity_pct: float | None,
) -> str:
    """Classify environmental reading quality based on presence, physics, and timestamps.

    Returns:
        One of 'valid', 'suspect', 'invalid', or 'missing'.
    """
    # 1. Missing data: both temperature and humidity are absent
    if temperature_c is None and relative_humidity_pct is None:
        return "missing"

    # 2. Temperature physical boundaries
    if temperature_c is not None:
        if math.isnan(temperature_c) or math.isinf(temperature_c):
            return "invalid"
        if temperature_c < TEMP_EXTREME_MIN or temperature_c > TEMP_EXTREME_MAX:
            return "invalid"
        if temperature_c < TEMP_PLAUSIBILITY_MIN or temperature_c > TEMP_PLAUSIBILITY_MAX:
            return "suspect"

    # 3. Humidity physical boundaries
    if relative_humidity_pct is not None:
        if math.isnan(relative_humidity_pct) or math.isinf(relative_humidity_pct):
            return "invalid"
        if relative_humidity_pct < 0.0 or relative_humidity_pct > 100.0:
            return "invalid"

    # 4. Timestamp sanity checks
    if measured_at is not None:
        if measured_at.tzinfo is None:
            measured_at = measured_at.replace(tzinfo=timezone.utc)

        # Implausible future clock drift
        if measured_at > received_at + MAX_EXTREME_CLOCK_DRIFT:
            return "invalid"
        if measured_at > received_at + MAX_FUTURE_CLOCK_DRIFT:
            return "suspect"

        # Implausible historical date (RTC defaulted to 1970 or 2000)
        if measured_at < EARLIEST_PLAUSIBLE_TIMESTAMP:
            return "suspect"

    return "valid"


def _check_payload_conflict(
    existing: SensorReading,
    payload: ReadingCreateRequest,
) -> None:
    """Verify that a retransmitted event contains identical data.

    Raises:
        ConflictException: If the duplicate payload contradicts previously recorded values.
    """
    # Compare temperature
    payload_temp = Decimal(str(payload.temperature_c)) if payload.temperature_c is not None else None
    if existing.temperature_c != payload_temp:
        raise ConflictException(
            f"Event ID '{payload.event_id}' was already recorded with conflicting temperature "
            f"({existing.temperature_c} °C vs retransmitted {payload_temp} °C)."
        )

    # Compare humidity
    payload_hum = Decimal(str(payload.relative_humidity_pct)) if payload.relative_humidity_pct is not None else None
    if existing.relative_humidity_pct != payload_hum:
        raise ConflictException(
            f"Event ID '{payload.event_id}' was already recorded with conflicting humidity "
            f"({existing.relative_humidity_pct} % vs retransmitted {payload_hum} %)."
        )

    # Compare measured_at if either is present
    if (existing.measured_at is None) != (payload.measured_at is None):
        raise ConflictException(
            f"Event ID '{payload.event_id}' was already recorded with conflicting measurement timestamp presence."
        )
    if existing.measured_at and payload.measured_at:
        # Normalize to UTC
        ex_time = existing.measured_at if existing.measured_at.tzinfo else existing.measured_at.replace(tzinfo=timezone.utc)
        pay_time = payload.measured_at if payload.measured_at.tzinfo else payload.measured_at.replace(tzinfo=timezone.utc)
        if abs((ex_time - pay_time).total_seconds()) > 1.0:
            raise ConflictException(
                f"Event ID '{payload.event_id}' was already recorded with conflicting measurement timestamp."
            )


def ingest_telemetry_reading(
    session: Session,
    device: Device,
    payload: ReadingCreateRequest,
) -> tuple[SensorReading, bool]:
    """Ingest, validate, and persist an environmental telemetry reading.

    Args:
        session: Active database session.
        device: Authenticated Device model instance.
        payload: Validated reading request payload.

    Returns:
        Tuple of (SensorReading, deduplicated_bool).
        deduplicated_bool is True if the event was an idempotent retry of an existing record.

    Raises:
        ConflictException: If an event ID collision occurs with differing payload values.
        ServiceUnavailableException: If persistence encounters an unrecoverable database failure.
    """
    received_at = datetime.now(timezone.utc)

    # Step 1: Query for existing reading by (device_id, event_id)
    existing = get_reading_by_device_and_event(session, device.id, payload.event_id)
    if existing is not None:
        _check_payload_conflict(existing, payload)
        logger.info(
            "Idempotent duplicate reading ingested for device_code=%s event_id=%s",
            device.device_code,
            payload.event_id,
        )
        return (existing, True)

    # Step 2: Quality assessment
    quality_status = assess_reading_quality(
        measured_at=payload.measured_at,
        received_at=received_at,
        temperature_c=payload.temperature_c,
        relative_humidity_pct=payload.relative_humidity_pct,
    )

    # Step 3: Transactional persistence with concurrent duplicate safety
    try:
        reading = create_reading(
            session=session,
            device_id=device.id,
            event_id=payload.event_id,
            measured_at=payload.measured_at,
            received_at=received_at,
            temperature_c=payload.temperature_c,
            relative_humidity_pct=payload.relative_humidity_pct,
            quality_status=quality_status,
            source_mode=payload.source_mode,
            firmware_version=payload.firmware_version,
        )

        # Update device heartbeat and status
        update_device_heartbeat(
            session=session,
            device_id=device.id,
            seen_at=received_at,
            firmware_version=payload.firmware_version,
        )

        session.commit()
        logger.info(
            "Successfully persisted reading device_code=%s event_id=%s quality=%s",
            device.device_code,
            payload.event_id,
            quality_status,
        )
        return (reading, False)

    except IntegrityError as exc:
        session.rollback()
        # Handle concurrent race condition where another request created the event concurrently
        concurrent_existing = get_reading_by_device_and_event(session, device.id, payload.event_id)
        if concurrent_existing is not None:
            _check_payload_conflict(concurrent_existing, payload)
            logger.info(
                "Resolved concurrent duplicate reading for device_code=%s event_id=%s",
                device.device_code,
                payload.event_id,
            )
            return (concurrent_existing, True)

        logger.error(
            "Database integrity error during reading persistence for device_code=%s: %s",
            device.device_code,
            type(exc).__name__,
        )
        raise ServiceUnavailableException("Failed to persist reading due to database integrity error.") from None

    except Exception as exc:
        session.rollback()
        logger.exception(
            "Unexpected error during reading persistence for device_code=%s: %s",
            device.device_code,
            type(exc).__name__,
        )
        raise ServiceUnavailableException("Database service error during reading persistence.") from None
