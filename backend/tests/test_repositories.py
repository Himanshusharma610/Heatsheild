"""Unit tests for repository data-access functions."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.repositories.alert import (
    acknowledge_alert,
    create_alert,
    create_alert_rule,
    get_active_alert_by_dedup_key,
    get_alert_by_id,
    get_alert_rule_by_id,
    list_active_alert_rules,
    list_alerts,
    resolve_alert,
)
from app.repositories.device import (
    deactivate_device,
    get_device_by_code,
    get_device_by_id,
    list_devices_by_worksite,
    register_device,
    update_device_heartbeat,
)
from app.repositories.reading import (
    create_reading,
    get_latest_valid_reading,
    get_reading_by_device_and_event,
    get_reading_by_id,
    get_reading_history,
)
from app.repositories.worksite import (
    create_worksite,
    deactivate_worksite,
    get_worksite_by_id,
    get_worksite_by_name,
    list_active_worksites,
)


@pytest.fixture
def db_session() -> Session:
    """Provide an isolated in-memory SQLite session with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_worksite_repository_crud(db_session: Session) -> None:
    """Verify worksite creation, retrieval, listing, and soft-deactivation."""
    worksite = create_worksite(
        db_session,
        name="Metro Construction Line 3",
        location_description="Station Central",
    )
    assert worksite.id is not None
    assert worksite.name == "Metro Construction Line 3"

    by_id = get_worksite_by_id(db_session, worksite.id)
    assert by_id is not None
    assert by_id.name == "Metro Construction Line 3"

    by_name = get_worksite_by_name(db_session, "Metro Construction Line 3")
    assert by_name is not None
    assert by_name.id == worksite.id

    active = list_active_worksites(db_session)
    assert len(active) == 1

    deactivated = deactivate_worksite(db_session, worksite.id)
    assert deactivated is not None
    assert deactivated.is_active is False

    active_after = list_active_worksites(db_session)
    assert len(active_after) == 0


def test_device_repository_crud(db_session: Session) -> None:
    """Verify device registration, heartbeat update, and soft-deactivation."""
    worksite = create_worksite(db_session, name="Foundry Zone B")

    device = register_device(
        db_session,
        device_code="HS-FD-001",
        worksite_id=worksite.id,
        display_name="Furnace Room Sensor",
        firmware_version="1.0.1",
    )
    assert device.device_code == "HS-FD-001"
    assert device.status == "registered"

    by_code = get_device_by_code(db_session, "HS-FD-001")
    assert by_code is not None
    assert by_code.id == device.id

    by_id = get_device_by_id(db_session, device.id)
    assert by_id is not None

    devices_list = list_devices_by_worksite(db_session, worksite.id)
    assert len(devices_list) == 1

    # Heartbeat
    now = datetime.now(timezone.utc)
    updated = update_device_heartbeat(db_session, device.id, seen_at=now, firmware_version="1.0.2")
    assert updated is not None
    assert updated.status == "online"
    assert updated.firmware_version == "1.0.2"

    # Deactivation
    deactivated = deactivate_device(db_session, device.id)
    assert deactivated is not None
    assert deactivated.is_active is False
    assert deactivated.status == "deactivated"


def test_sensor_reading_repository_queries(db_session: Session) -> None:
    """Verify sensor reading creation, deduplication lookup, and history ordering."""
    worksite = create_worksite(db_session, name="Refinery North")
    device = register_device(db_session, device_code="HS-REF-001", worksite_id=worksite.id)

    t1 = datetime(2026, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 11, 15, 10, 5, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 11, 15, 10, 10, 0, tzinfo=timezone.utc)

    # 1. Valid reading
    r1 = create_reading(
        db_session,
        device_id=device.id,
        event_id="evt-001",
        measured_at=t1,
        temperature_c=Decimal("35.20"),
        relative_humidity_pct=Decimal("55.00"),
        quality_status="valid",
    )
    assert r1.id is not None

    # 2. Suspect reading
    create_reading(
        db_session,
        device_id=device.id,
        event_id="evt-002",
        measured_at=t2,
        temperature_c=Decimal("58.00"),
        relative_humidity_pct=Decimal("95.00"),
        quality_status="suspect",
    )

    # 3. Later valid reading
    create_reading(
        db_session,
        device_id=device.id,
        event_id="evt-003",
        measured_at=t3,
        temperature_c=Decimal("37.10"),
        relative_humidity_pct=Decimal("52.40"),
        quality_status="valid",
    )

    # Deduplication lookup
    dup = get_reading_by_device_and_event(db_session, device.id, "evt-001")
    assert dup is not None
    assert dup.id == r1.id

    # Latest valid reading should be evt-003
    latest_valid = get_latest_valid_reading(db_session, device.id)
    assert latest_valid is not None
    assert latest_valid.event_id == "evt-003"
    assert latest_valid.quality_status == "valid"

    # History query
    history = get_reading_history(db_session, device.id)
    assert len(history) == 3

    # History with quality filter
    valid_history = get_reading_history(db_session, device.id, quality_status="valid")
    assert len(valid_history) == 2


def test_alert_and_rule_repository(db_session: Session) -> None:
    """Verify alert rule creation, alert triggering, acknowledgement, and resolution."""
    worksite = create_worksite(db_session, name="Assembly Plant 4")
    device = register_device(db_session, device_code="HS-ASM-001", worksite_id=worksite.id)

    # Create rule
    rule = create_alert_rule(
        db_session,
        name="High Ambient Heat",
        metric="temperature_c",
        operator="gt",
        severity="warning",
        worksite_id=worksite.id,
        threshold_value=Decimal("40.00"),
    )
    assert rule.id is not None
    assert rule.rule_version == 1

    by_id = get_alert_rule_by_id(db_session, rule.id)
    assert by_id is not None
    assert by_id.name == "High Ambient Heat"

    rules = list_active_alert_rules(db_session, worksite_id=worksite.id)
    assert len(rules) == 1

    # Create alert
    dedup = f"{device.id}:threshold_exceeded:temperature_c"
    alert = create_alert(
        db_session,
        device_id=device.id,
        event_type="threshold_exceeded",
        severity="warning",
        status="triggered",
        alert_rule_id=rule.id,
        rule_version_snapshot=rule.rule_version,
        deduplication_key=dedup,
    )
    assert alert.id is not None
    assert alert.status == "triggered"

    # Dedup lookup
    active_alert = get_active_alert_by_dedup_key(db_session, dedup)
    assert active_alert is not None
    assert active_alert.id == alert.id

    # Acknowledge
    ack = acknowledge_alert(
        db_session,
        alert_id=alert.id,
        actor_id=None,
        action_taken="Ceased heavy physical tasks and distributed electrolyte hydration.",
    )
    assert ack.id is not None
    assert alert.status == "acknowledged"
    assert alert.acknowledged_at is not None

    # Resolve
    resolved = resolve_alert(db_session, alert.id)
    assert resolved is not None
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None

    # Once resolved, active dedup lookup returns None
    no_active = get_active_alert_by_dedup_key(db_session, dedup)
    assert no_active is None
