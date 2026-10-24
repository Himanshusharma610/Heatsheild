"""Integration tests against a real PostgreSQL 15 database instance.

Verifies PostgreSQL-specific constraints, foreign key RESTRICT rules,
unique event deduplication, check constraints, JSONB storage, and transaction rollbacks.
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
import uuid
import pytest
import psycopg2
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.alert import Alert, AlertRule
from app.models.device import Device
from app.models.reading import SensorReading
from app.models.worksite import Worksite
from app.repositories.alert import create_alert_rule
from app.repositories.device import register_device
from app.repositories.reading import (
    create_reading,
    get_latest_valid_reading,
    get_reading_history,
)
from app.repositories.worksite import create_worksite

POSTGRES_TEST_URL = os.environ.get(
    "POSTGRES_TEST_URL",
    "postgresql+psycopg2://heatshield_test:heatshield_test_pw@127.0.0.1:54332/heatshield_test",
)


def is_postgres_available() -> bool:
    """Check if the target PostgreSQL server is accessible."""
    try:
        raw_url = POSTGRES_TEST_URL.replace("postgresql+psycopg2://", "postgresql://")
        conn = psycopg2.connect(raw_url, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


postgres_required = pytest.mark.skipif(
    not is_postgres_available(),
    reason="Dedicated PostgreSQL test database is not accessible at 127.0.0.1:54332",
)


@pytest.fixture(scope="module")
def pg_engine():
    """Create a module-scoped PostgreSQL engine."""
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_session(pg_engine) -> Session:
    """Provide a transactional session for a single test that cleans up after itself."""
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    session = session_factory()
    yield session
    session.rollback()
    session.close()


@postgres_required
def test_postgres_worksite_device_foreign_key_restrict(pg_session: Session) -> None:
    """Verify PostgreSQL enforces ON DELETE RESTRICT on worksites referenced by devices."""
    worksite = create_worksite(pg_session, name=f"FK Test Site {uuid.uuid4().hex[:6]}")
    device = register_device(
        pg_session,
        device_code=f"HS-FK-{uuid.uuid4().hex[:6]}",
        worksite_id=worksite.id,
    )
    pg_session.commit()

    # Attempting to delete the worksite while a device is attached must raise IntegrityError
    pg_session.delete(worksite)
    with pytest.raises(IntegrityError):
        pg_session.commit()

    pg_session.rollback()

    # Verify entities still exist
    assert pg_session.get(Worksite, worksite.id) is not None
    assert pg_session.get(Device, device.id) is not None


@postgres_required
def test_postgres_reading_deduplication_unique_constraint(pg_session: Session) -> None:
    """Verify PostgreSQL enforces UNIQUE (device_id, event_id) and transaction rolls back cleanly."""
    worksite = create_worksite(pg_session, name=f"Dedup Site {uuid.uuid4().hex[:6]}")
    device = register_device(
        pg_session,
        device_code=f"HS-DEDUP-{uuid.uuid4().hex[:6]}",
        worksite_id=worksite.id,
    )
    pg_session.commit()

    event_id = "evt-pg-unique-001"
    create_reading(
        pg_session,
        device_id=device.id,
        event_id=event_id,
        temperature_c=Decimal("34.50"),
        relative_humidity_pct=Decimal("60.00"),
    )
    pg_session.commit()

    # Attempting to insert duplicate (device_id, event_id)
    with pytest.raises(IntegrityError) as exc_info:
        create_reading(
            pg_session,
            device_id=device.id,
            event_id=event_id,
            temperature_c=Decimal("34.50"),
            relative_humidity_pct=Decimal("60.00"),
        )
        pg_session.commit()

    assert "uq_readings_device_event" in str(exc_info.value).lower()
    pg_session.rollback()

    # Verify session recovered and subsequent query works
    readings = pg_session.scalars(select(SensorReading).where(SensorReading.device_id == device.id)).all()
    assert len(readings) == 1


@postgres_required
def test_postgres_check_constraint_humidity_range(pg_session: Session) -> None:
    """Verify PostgreSQL rejects relative_humidity_pct exceeding 100%."""
    worksite = create_worksite(pg_session, name=f"Check Site {uuid.uuid4().hex[:6]}")
    device = register_device(
        pg_session,
        device_code=f"HS-CK-{uuid.uuid4().hex[:6]}",
        worksite_id=worksite.id,
    )
    pg_session.commit()

    # Try inserting humidity 150%
    with pytest.raises(IntegrityError) as exc_info:
        create_reading(
            pg_session,
            device_id=device.id,
            event_id="evt-invalid-hum",
            temperature_c=Decimal("30.00"),
            relative_humidity_pct=Decimal("150.00"),
        )
        pg_session.commit()

    assert "ck_readings_humidity_range" in str(exc_info.value).lower()
    pg_session.rollback()


@postgres_required
def test_postgres_check_constraint_quality_status(pg_session: Session) -> None:
    """Verify PostgreSQL rejects invalid quality_status values."""
    worksite = create_worksite(pg_session, name=f"Quality Site {uuid.uuid4().hex[:6]}")
    device = register_device(
        pg_session,
        device_code=f"HS-Q-{uuid.uuid4().hex[:6]}",
        worksite_id=worksite.id,
    )
    pg_session.commit()

    # Try inserting unsupported quality_status
    with pytest.raises(IntegrityError) as exc_info:
        create_reading(
            pg_session,
            device_id=device.id,
            event_id="evt-invalid-q",
            temperature_c=Decimal("30.00"),
            quality_status="unsupported_status",
        )
        pg_session.commit()

    assert "ck_readings_quality_status" in str(exc_info.value).lower()
    pg_session.rollback()


@postgres_required
def test_postgres_jsonb_storage_and_query(pg_session: Session) -> None:
    """Verify JSONB column stores complex parameters in PostgreSQL."""
    rule = create_alert_rule(
        pg_session,
        name="Dynamic WBGT Threshold",
        metric="heat_index",
        operator="gte",
        severity="critical",
        threshold_value=Decimal("42.00"),
        threshold_params={
            "sustained_duration_minutes": 15,
            "consecutive_readings": 3,
            "work_rest_cycle": "15m_rest_per_hour",
        },
    )
    pg_session.commit()

    retrieved = pg_session.get(AlertRule, rule.id)
    assert retrieved is not None
    assert retrieved.threshold_params["sustained_duration_minutes"] == 15
    assert retrieved.threshold_params["work_rest_cycle"] == "15m_rest_per_hour"


@postgres_required
def test_postgres_timezone_aware_queries(pg_session: Session) -> None:
    """Verify UTC TIMESTAMPTZ storage and time-range query retrieval in PostgreSQL."""
    worksite = create_worksite(pg_session, name=f"TZ Site {uuid.uuid4().hex[:6]}")
    device = register_device(
        pg_session,
        device_code=f"HS-TZ-{uuid.uuid4().hex[:6]}",
        worksite_id=worksite.id,
    )
    pg_session.commit()

    t1 = datetime(2026, 11, 15, 8, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 11, 15, 9, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 11, 15, 10, 0, 0, tzinfo=timezone.utc)

    create_reading(pg_session, device.id, "tz-1", measured_at=t1, temperature_c=Decimal("30.00"), quality_status="valid")
    create_reading(pg_session, device.id, "tz-2", measured_at=t2, temperature_c=Decimal("35.00"), quality_status="valid")
    create_reading(pg_session, device.id, "tz-3", measured_at=t3, temperature_c=Decimal("40.00"), quality_status="valid")
    pg_session.commit()

    # Query latest reading
    latest = get_latest_valid_reading(pg_session, device.id)
    assert latest is not None
    assert latest.event_id == "tz-3"
    assert latest.received_at.tzinfo is not None

    # Query history
    history = get_reading_history(pg_session, device.id)
    assert len(history) == 3
