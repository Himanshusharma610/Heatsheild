"""Unit tests for SQLAlchemy ORM models."""

from datetime import datetime, timezone
from decimal import Decimal
import uuid

from app.models.alert import Alert, AlertAcknowledgement, AlertRule
from app.models.audit import AuditLog
from app.models.device import Device
from app.models.reading import SensorReading
from app.models.user import User
from app.models.worksite import Worksite


def test_worksite_model_instantiation() -> None:
    """Verify Worksite model fields and defaults."""
    worksite = Worksite(
        name="Unit Test Construction Site",
        location_description="Plot 42, Industrial Zone",
        is_active=True,
    )
    assert worksite.name == "Unit Test Construction Site"
    assert worksite.is_active is True
    assert "Unit Test Construction Site" in repr(worksite)


def test_device_model_instantiation() -> None:
    """Verify Device model fields and status values."""
    w_id = uuid.uuid4()
    device = Device(
        device_code="HS-TEST-001",
        worksite_id=w_id,
        display_name="Site 1 North Sensor",
        status="registered",
        firmware_version="1.0.0",
        is_active=True,
    )
    assert device.device_code == "HS-TEST-001"
    assert device.worksite_id == w_id
    assert device.status == "registered"
    assert "HS-TEST-001" in repr(device)


def test_sensor_reading_model_instantiation() -> None:
    """Verify SensorReading model temperature, humidity, and quality status."""
    d_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    reading = SensorReading(
        device_id=d_id,
        event_id="evt-1001",
        measured_at=now,
        temperature_c=Decimal("38.50"),
        relative_humidity_pct=Decimal("65.20"),
        quality_status="valid",
        source_mode="hardware",
        firmware_version="1.0.0",
    )
    assert reading.device_id == d_id
    assert reading.event_id == "evt-1001"
    assert reading.temperature_c == Decimal("38.50")
    assert reading.relative_humidity_pct == Decimal("65.20")
    assert reading.quality_status == "valid"
    assert reading.source_mode == "hardware"
    assert "evt-1001" in repr(reading)


def test_alert_rule_and_alert_models() -> None:
    """Verify AlertRule and Alert models and independent severity/status."""
    d_id = uuid.uuid4()
    rule = AlertRule(
        name="Extreme Heat Alert",
        metric="temperature_c",
        operator="gt",
        threshold_value=Decimal("45.00"),
        severity="critical",
        is_enabled=True,
    )
    assert rule.metric == "temperature_c"
    assert rule.severity == "critical"
    assert rule.rule_version == 1

    alert = Alert(
        device_id=d_id,
        event_type="threshold_exceeded",
        severity="critical",
        status="triggered",
        deduplication_key=f"{d_id}:threshold_exceeded:temperature_c",
    )
    assert alert.severity == "critical"
    assert alert.status == "triggered"
    assert "critical" in repr(alert)


def test_user_model_security_repr() -> None:
    """Verify User model never leaks password hash in string representations."""
    user = User(
        email="supervisor@heatshield.gov.in",
        display_name="Site Supervisor",
        password_hash="$2b$12$e80yVv5aK...sensitive_hash...",
        role="supervisor",
        is_active=True,
    )
    user_repr = repr(user)
    user_str = str(user)

    assert "supervisor@heatshield.gov.in" in user_repr
    assert "sensitive_hash" not in user_repr
    assert "sensitive_hash" not in user_str


def test_audit_log_model() -> None:
    """Verify AuditLog structure and extra_data JSON mapping."""
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()
    log = AuditLog(
        actor_id=actor_id,
        action_type="device.register",
        target_entity_type="device",
        target_entity_id=target_id,
        extra_data={"device_code": "HS-TEST-002"},
    )
    assert log.action_type == "device.register"
    assert log.extra_data == {"device_code": "HS-TEST-002"}
    assert "device.register" in repr(log)
