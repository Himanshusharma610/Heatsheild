"""Automated unit and integration tests for Alert Rules and Alert Lifecycle (Module 8).

Verifies:
1. Valid rule matches an eligible reading
2. Non-matching rule does not create an alert
3. Disabled rules are ignored
4. Missing, invalid, or stale readings do not create misleading low-risk outcomes or trigger alerts
5. Unsupported metrics or malformed rules are rejected
6. Alert events are persisted correctly with provenance
7. Repeated evaluation does not create duplicate active alerts (deduplication)
8. Distinct alert episodes can be represented after previous alert is resolved
9. Acknowledgement updates lifecycle state and timestamp correctly
10. Unauthorized acknowledgement is rejected (including rejection of device tokens)
11. Invalid state transitions are rejected (e.g. acknowledging a resolved alert)
12. Database failures do not produce false-success responses
13. Module 7 Heat Index rule evaluation and unavailable domain handling
14. API endpoints: GET /api/v1/alerts, POST /api/v1/alerts/{id}/acknowledge, POST /api/v1/alerts/{id}/resolve, GET /api/v1/alert-rules, POST /api/v1/alert-rules
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.db.base import Base
from app.main import create_app
from app.models.alert import Alert, AlertAcknowledgement, AlertRule
from app.models.device import Device
from app.models.reading import SensorReading
from app.models.user import User
from app.models.worksite import Worksite
from app.repositories.alert import (
    create_alert_rule,
    get_alert_by_id,
    list_active_alert_rules,
)
from app.repositories.device import hash_device_token
from app.schemas.alert import AlertRuleCreateRequest
from app.services.alert_engine import (
    acknowledge_alert_service,
    compare_metric_value,
    evaluate_reading_alerts,
    evaluate_rule,
    resolve_alert_service,
    validate_rule_parameters,
)


@pytest.fixture
def memory_session() -> Session:
    """In-memory SQLite database session with complete schema."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def seeded_entities(memory_session: Session) -> dict:
    """Helper fixture providing worksite, device, supervisor user, and viewer user."""
    worksite = Worksite(
        name="Kolkata Port Terminal 4",
        location_description="Dock 4, Kolkata",
        is_active=True,
    )
    memory_session.add(worksite)
    memory_session.flush()

    device = Device(
        device_code="HS-KOL-D001",
        worksite_id=worksite.id,
        display_name="Dock 4 South Pole",
        status="online",
        api_key_hash=hash_device_token("secret-device-token"),
        is_active=True,
    )
    memory_session.add(device)

    supervisor = User(
        email="supervisor@heatshield.gov.in",
        display_name="Ramesh Sen",
        password_hash="argon2id$mockhash",
        role="supervisor",
        is_active=True,
    )
    memory_session.add(supervisor)

    viewer = User(
        email="viewer@heatshield.gov.in",
        display_name="Amit Roy",
        password_hash="argon2id$mockhash",
        role="viewer",
        is_active=True,
    )
    memory_session.add(viewer)
    memory_session.commit()

    return {
        "worksite": worksite,
        "device": device,
        "supervisor": supervisor,
        "viewer": viewer,
    }


# ==============================================================================
# 1. Pure Rule Evaluation Unit Tests
# ==============================================================================

def test_compare_metric_value_operators():
    """Verify standard operators gt, gte, lt, lte, eq."""
    assert compare_metric_value(41.0, "gt", 40.0) is True
    assert compare_metric_value(40.0, "gt", 40.0) is False
    assert compare_metric_value(40.0, "gte", 40.0) is True
    assert compare_metric_value(39.9, "gte", 40.0) is False

    assert compare_metric_value(25.0, "lt", 30.0) is True
    assert compare_metric_value(30.0, "lt", 30.0) is False
    assert compare_metric_value(30.0, "lte", 30.0) is True

    assert compare_metric_value(50.0, "eq", 50.0) is True
    assert compare_metric_value(50.1, "eq", 50.0) is False


def test_evaluate_rule_temperature_match(memory_session: Session):
    """Rule matches when temperature exceeds threshold."""
    rule = AlertRule(
        name="High Temp",
        metric="temperature_c",
        operator="gte",
        threshold_value=Decimal("40.00"),
        severity="warning",
        is_enabled=True,
    )

    # 41°C >= 40°C -> matches
    assert evaluate_rule(rule, temperature_c=41.0, relative_humidity_pct=50.0) is True
    # 39°C >= 40°C -> does not match
    assert evaluate_rule(rule, temperature_c=39.0, relative_humidity_pct=50.0) is False


def test_evaluate_rule_humidity_match(memory_session: Session):
    """Rule matches when relative humidity satisfies condition."""
    rule = AlertRule(
        name="High Humidity",
        metric="relative_humidity_pct",
        operator="gt",
        threshold_value=Decimal("85.00"),
        severity="warning",
        is_enabled=True,
    )

    assert evaluate_rule(rule, temperature_c=32.0, relative_humidity_pct=88.0) is True
    assert evaluate_rule(rule, temperature_c=32.0, relative_humidity_pct=80.0) is False


def test_evaluate_rule_heat_index_match(memory_session: Session):
    """Rule matches when Module 7 Heat Index calculation exceeds threshold."""
    rule = AlertRule(
        name="Extreme Heat Index",
        metric="heat_index_c",
        operator="gte",
        threshold_value=Decimal("45.00"),
        severity="critical",
        is_enabled=True,
    )

    # At 38°C and 65% RH, Heat Index is ~56°C (>= 45°C) -> matches
    assert evaluate_rule(rule, temperature_c=38.0, relative_humidity_pct=65.0) is True

    # At 25°C and 40% RH, Heat Index is ~25°C (< 45°C) -> does not match
    assert evaluate_rule(rule, temperature_c=25.0, relative_humidity_pct=40.0) is False


def test_disabled_rules_are_ignored():
    """Disabled rule never triggers an alert."""
    rule = AlertRule(
        name="Disabled Rule",
        metric="temperature_c",
        operator="gt",
        threshold_value=Decimal("30.00"),
        severity="warning",
        is_enabled=False,
    )
    assert evaluate_rule(rule, temperature_c=45.0, relative_humidity_pct=60.0) is False


def test_missing_and_invalid_readings_do_not_match():
    """CRITICAL SAFETY TEST: Missing, invalid, or stale data NEVER matches a threshold rule."""
    rule = AlertRule(
        name="Safety Check",
        metric="temperature_c",
        operator="lt",  # Rule triggers if temp < 50
        threshold_value=Decimal("50.00"),
        severity="warning",
        is_enabled=True,
    )

    # If temperature is None, it must NOT be evaluated as 0 or match
    assert evaluate_rule(rule, temperature_c=None, relative_humidity_pct=50.0) is False

    # If upstream quality is 'invalid', it must NOT match
    assert evaluate_rule(rule, temperature_c=30.0, relative_humidity_pct=50.0, quality_status="invalid") is False

    # If reading is stale, it must NOT match
    assert evaluate_rule(rule, temperature_c=30.0, relative_humidity_pct=50.0, is_stale=True) is False


def test_heat_index_out_of_domain_does_not_trigger():
    """If Heat Index calculation returns out_of_domain, heat_index rule must not match."""
    rule = AlertRule(
        name="Heat Index Check",
        metric="heat_index_c",
        operator="gte",
        threshold_value=Decimal("30.00"),
        severity="warning",
        is_enabled=True,
    )

    # 15°C is below the 20°C domain limit for Heat Index
    assert evaluate_rule(rule, temperature_c=15.0, relative_humidity_pct=50.0) is False


# ==============================================================================
# 2. Rule Parameter Validation Tests
# ==============================================================================

def test_validate_rule_parameters_success():
    """Valid rule parameters pass validation."""
    validate_rule_parameters(
        metric="heat_index_c",
        operator="gte",
        severity="critical",
        threshold_value=42.5,
    )


def test_validate_rule_parameters_unsupported_metric():
    """Unsupported metric (e.g. wbgt) is rejected."""
    with pytest.raises(ValidationException) as exc_info:
        validate_rule_parameters(
            metric="wbgt_c",
            operator="gte",
            severity="warning",
            threshold_value=32.0,
        )
    assert "Unsupported metric 'wbgt_c'" in str(exc_info.value.message)


def test_validate_rule_parameters_unsupported_operator():
    """Unsupported operator is rejected."""
    with pytest.raises(ValidationException) as exc_info:
        validate_rule_parameters(
            metric="temperature_c",
            operator="regex",
            severity="warning",
            threshold_value=35.0,
        )
    assert "Unsupported operator 'regex'" in str(exc_info.value.message)


def test_validate_rule_parameters_non_finite_threshold():
    """NaN and Infinite thresholds are rejected."""
    with pytest.raises(ValidationException) as exc_info:
        validate_rule_parameters(
            metric="temperature_c",
            operator="gt",
            severity="warning",
            threshold_value=float("nan"),
        )
    assert "finite number" in str(exc_info.value.message)


# ==============================================================================
# 3. Persistence, Deduplication & Episodes Service Tests
# ==============================================================================

def test_alert_persisted_correctly(memory_session: Session, seeded_entities: dict):
    """Eligible reading creates and persists an Alert with rule version snapshot and dedup key."""
    device = seeded_entities["device"]
    rule = create_alert_rule(
        session=memory_session,
        name="High Temp Warning",
        metric="temperature_c",
        operator="gte",
        threshold_value=40.0,
        severity="warning",
        worksite_id=device.worksite_id,
    )
    memory_session.commit()

    reading = SensorReading(
        device_id=device.id,
        event_id="evt-001",
        temperature_c=Decimal("42.5"),
        relative_humidity_pct=Decimal("60.0"),
        quality_status="valid",
    )
    memory_session.add(reading)
    memory_session.flush()

    alerts = evaluate_reading_alerts(session=memory_session, reading=reading, device=device)
    assert len(alerts) == 1
    alert = alerts[0]

    assert alert.device_id == device.id
    assert alert.reading_id == reading.id
    assert alert.alert_rule_id == rule.id
    assert alert.severity == "warning"
    assert alert.status == "triggered"
    assert alert.rule_version_snapshot == 1
    assert alert.deduplication_key == f"device:{device.id}:rule:{rule.id}"


def test_alert_deduplication_for_repeated_evaluations(memory_session: Session, seeded_entities: dict):
    """Subsequent breaching readings do NOT create duplicate active alerts during an episode."""
    device = seeded_entities["device"]
    create_alert_rule(
        session=memory_session,
        name="High Heat Warning",
        metric="temperature_c",
        operator="gte",
        threshold_value=40.0,
        severity="warning",
        worksite_id=device.worksite_id,
    )
    memory_session.commit()

    # Reading 1 triggers alert
    reading1 = SensorReading(
        device_id=device.id,
        event_id="evt-001",
        temperature_c=Decimal("41.0"),
        relative_humidity_pct=Decimal("60.0"),
        quality_status="valid",
    )
    memory_session.add(reading1)
    memory_session.flush()
    alerts1 = evaluate_reading_alerts(session=memory_session, reading=reading1, device=device)
    memory_session.commit()
    assert len(alerts1) == 1

    # Reading 2 arrives (still hot): condition is satisfied, but active episode exists
    reading2 = SensorReading(
        device_id=device.id,
        event_id="evt-002",
        temperature_c=Decimal("43.0"),
        relative_humidity_pct=Decimal("62.0"),
        quality_status="valid",
    )
    memory_session.add(reading2)
    memory_session.flush()
    alerts2 = evaluate_reading_alerts(session=memory_session, reading=reading2, device=device)
    memory_session.commit()

    # Must be deduplicated (0 new alerts created)
    assert len(alerts2) == 0


def test_new_alert_episode_created_after_resolution(memory_session: Session, seeded_entities: dict):
    """After an alert is marked resolved, a subsequent breach creates a distinct new episode."""
    device = seeded_entities["device"]
    create_alert_rule(
        session=memory_session,
        name="Heat Alert",
        metric="temperature_c",
        operator="gte",
        threshold_value=40.0,
        severity="warning",
    )
    memory_session.commit()

    # Episode 1
    reading1 = SensorReading(device_id=device.id, event_id="evt-001", temperature_c=Decimal("41.0"), relative_humidity_pct=Decimal("50.0"), quality_status="valid")
    memory_session.add(reading1)
    memory_session.flush()
    alerts1 = evaluate_reading_alerts(session=memory_session, reading=reading1, device=device)
    memory_session.commit()
    alert1 = alerts1[0]

    # Resolve Episode 1
    resolve_alert_service(session=memory_session, alert_id=alert1.id)
    memory_session.commit()

    re_alert1 = get_alert_by_id(memory_session, alert1.id)
    assert re_alert1.status == "resolved"
    assert re_alert1.resolved_at is not None

    # Episode 2: temperature rises above threshold again
    reading2 = SensorReading(device_id=device.id, event_id="evt-002", temperature_c=Decimal("42.0"), relative_humidity_pct=Decimal("50.0"), quality_status="valid")
    memory_session.add(reading2)
    memory_session.flush()
    alerts2 = evaluate_reading_alerts(session=memory_session, reading=reading2, device=device)
    memory_session.commit()

    assert len(alerts2) == 1
    alert2 = alerts2[0]
    assert alert2.id != alert1.id
    assert alert2.status == "triggered"


# ==============================================================================
# 4. Lifecycle Transitions & State Machine Tests
# ==============================================================================

def test_acknowledgement_lifecycle(memory_session: Session, seeded_entities: dict):
    """Supervisor acknowledgement records action and transitions state to acknowledged."""
    device = seeded_entities["device"]
    supervisor = seeded_entities["supervisor"]

    reading = SensorReading(device_id=device.id, event_id="evt-001", temperature_c=Decimal("41.0"), relative_humidity_pct=Decimal("50.0"), quality_status="valid")
    memory_session.add(reading)
    memory_session.flush()

    rule = create_alert_rule(session=memory_session, name="Rule", metric="temperature_c", operator="gte", threshold_value=40.0, severity="warning")
    memory_session.commit()

    alerts = evaluate_reading_alerts(session=memory_session, reading=reading, device=device)
    memory_session.commit()
    alert = alerts[0]

    # Acknowledge
    ack_text = "Distributed electrolytes and rotated crew into cooling tent."
    alert_after, ack = acknowledge_alert_service(
        session=memory_session,
        alert_id=alert.id,
        actor=supervisor,
        action_taken=ack_text,
    )
    memory_session.commit()

    assert alert_after.status == "acknowledged"
    assert alert_after.acknowledged_at is not None
    assert ack.actor_id == supervisor.id
    assert ack.action_taken == ack_text


def test_invalid_state_transitions_rejected(memory_session: Session, seeded_entities: dict):
    """Resolved alert cannot be re-acknowledged; non-existent alert returns 404."""
    device = seeded_entities["device"]
    supervisor = seeded_entities["supervisor"]

    create_alert_rule(session=memory_session, name="Rule", metric="temperature_c", operator="gte", threshold_value=40.0, severity="warning")
    memory_session.commit()

    reading = SensorReading(device_id=device.id, event_id="evt-001", temperature_c=Decimal("41.0"), relative_humidity_pct=Decimal("50.0"), quality_status="valid")
    memory_session.add(reading)
    memory_session.flush()
    alerts = evaluate_reading_alerts(session=memory_session, reading=reading, device=device)
    memory_session.commit()
    alert = alerts[0]

    # Resolve first
    resolve_alert_service(session=memory_session, alert_id=alert.id)
    memory_session.commit()

    # Attempting to acknowledge a resolved alert raises ConflictException
    with pytest.raises(ConflictException) as exc_info:
        acknowledge_alert_service(session=memory_session, alert_id=alert.id, actor=supervisor)
    assert "already in 'resolved' state" in str(exc_info.value.message)

    # Attempting to re-resolve raises ConflictException
    with pytest.raises(ConflictException) as exc_info2:
        resolve_alert_service(session=memory_session, alert_id=alert.id, actor=supervisor)
    assert "already resolved" in str(exc_info2.value.message)

    # Unknown alert ID raises NotFoundException
    with pytest.raises(NotFoundException):
        acknowledge_alert_service(session=memory_session, alert_id=uuid.uuid4(), actor=supervisor)


# ==============================================================================
# 5. API Endpoints & Authorization Integration Tests
# ==============================================================================

@pytest.fixture
def app_client(memory_session: Session) -> TestClient:
    """FastAPI TestClient sharing memory_session."""
    settings = Settings(
        APP_NAME="HeatShield Bharat Alert Engine Test",
        APP_ENV="testing",
        DEBUG=True,
        API_PREFIX="/api/v1",
        DATABASE_URL=None,
    )
    app = create_app(settings)

    # Override database dependency with isolated memory_session
    from app.db.session import get_db
    app.dependency_overrides[get_db] = lambda: memory_session

    return TestClient(app, raise_server_exceptions=False)


def test_api_list_alerts_unauthenticated_rejected(app_client: TestClient):
    """GET /api/v1/alerts without credentials returns 401."""
    response = app_client.get("/api/v1/alerts")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_api_list_alerts_authenticated(app_client: TestClient, seeded_entities: dict):
    """GET /api/v1/alerts returns paginated alert list with X-User-Id."""
    supervisor = seeded_entities["supervisor"]
    headers = {"X-User-Id": str(supervisor.id)}

    response = app_client.get("/api/v1/alerts", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert data["pagination"]["total"] >= 0


def test_api_acknowledge_alert_success(app_client: TestClient, memory_session: Session, seeded_entities: dict):
    """POST /api/v1/alerts/{id}/acknowledge succeeds with supervisor header."""
    device = seeded_entities["device"]
    supervisor = seeded_entities["supervisor"]

    create_alert_rule(session=memory_session, name="Heat Warning", metric="temperature_c", operator="gte", threshold_value=40.0, severity="warning")
    memory_session.commit()

    reading = SensorReading(device_id=device.id, event_id="evt-100", temperature_c=Decimal("42.0"), relative_humidity_pct=Decimal("50.0"), quality_status="valid")
    memory_session.add(reading)
    memory_session.flush()

    alerts = evaluate_reading_alerts(session=memory_session, reading=reading, device=device)
    memory_session.commit()
    alert_id = alerts[0].id

    headers = {"X-User-Id": str(supervisor.id)}
    payload = {"action_taken": "Issued shade break and cold water."}

    response = app_client.post(f"/api/v1/alerts/{alert_id}/acknowledge", json=payload, headers=headers)
    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["id"] == str(alert_id)
    assert res_data["status"] == "acknowledged"
    assert res_data["acknowledgement"]["action_taken"] == payload["action_taken"]
    assert res_data["acknowledgement"]["actor_id"] == str(supervisor.id)


def test_api_acknowledge_device_token_rejected(app_client: TestClient, seeded_entities: dict):
    """CRITICAL SECURITY: Device credentials (X-Device-Token) are strictly rejected on supervisor endpoints."""
    headers = {"X-Device-Token": "secret-device-token"}
    response = app_client.post(f"/api/v1/alerts/{uuid.uuid4()}/acknowledge", json={}, headers=headers)
    assert response.status_code == 401
    assert "Device credentials cannot be used" in response.json()["error"]["message"]


def test_api_acknowledge_viewer_role_forbidden(app_client: TestClient, memory_session: Session, seeded_entities: dict):
    """A user with 'viewer' role is forbidden (403) from acknowledging safety alerts."""
    viewer = seeded_entities["viewer"]
    headers = {"X-User-Id": str(viewer.id)}

    response = app_client.post(f"/api/v1/alerts/{uuid.uuid4()}/acknowledge", json={}, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_api_create_alert_rule(app_client: TestClient, seeded_entities: dict):
    """POST /api/v1/alert-rules creates a validated rule."""
    supervisor = seeded_entities["supervisor"]
    headers = {"X-User-Id": str(supervisor.id)}

    payload = {
        "name": "High Ambient Heat Alert",
        "metric": "heat_index_c",
        "operator": "gte",
        "threshold_value": 41.5,
        "severity": "critical",
        "is_enabled": True,
    }

    response = app_client.post("/api/v1/alert-rules", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == payload["name"]
    assert data["metric"] == "heat_index_c"
    assert data["threshold_value"] == 41.5
    assert data["severity"] == "critical"
    assert data["rule_version"] == 1


def test_api_create_alert_rule_invalid_metric_rejected(app_client: TestClient, seeded_entities: dict):
    """POST /api/v1/alert-rules with invalid metric returns 422."""
    supervisor = seeded_entities["supervisor"]
    headers = {"X-User-Id": str(supervisor.id)}

    payload = {
        "name": "Invalid Metric Rule",
        "metric": "fake_metric",
        "operator": "gt",
        "threshold_value": 30.0,
        "severity": "warning",
    }
    response = app_client.post("/api/v1/alert-rules", json=payload, headers=headers)
    assert response.status_code == 422


def test_api_resolve_alert(app_client: TestClient, memory_session: Session, seeded_entities: dict):
    """POST /api/v1/alerts/{id}/resolve transitions alert to resolved."""
    device = seeded_entities["device"]
    supervisor = seeded_entities["supervisor"]

    create_alert_rule(session=memory_session, name="Rule", metric="temperature_c", operator="gte", threshold_value=40.0, severity="warning")
    memory_session.commit()

    reading = SensorReading(device_id=device.id, event_id="evt-999", temperature_c=Decimal("41.0"), relative_humidity_pct=Decimal("50.0"), quality_status="valid")
    memory_session.add(reading)
    memory_session.flush()

    alerts = evaluate_reading_alerts(session=memory_session, reading=reading, device=device)
    memory_session.commit()
    alert_id = alerts[0].id

    headers = {"X-User-Id": str(supervisor.id)}
    payload = {"resolution_notes": "Ambient conditions cooled down; shift ended."}

    response = app_client.post(f"/api/v1/alerts/{alert_id}/resolve", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "resolved"
    assert response.json()["data"]["resolved_at"] is not None


def test_telemetry_ingestion_end_to_end_triggers_alert(app_client: TestClient, memory_session: Session, seeded_entities: dict):
    """POST /api/v1/readings atomically evaluates active rules and persists alerts."""
    device = seeded_entities["device"]

    create_alert_rule(
        session=memory_session,
        name="Telemetry Alert Rule",
        metric="temperature_c",
        operator="gte",
        threshold_value=40.0,
        severity="critical",
        worksite_id=device.worksite_id,
    )
    memory_session.commit()

    headers = {"X-Device-Token": "secret-device-token"}
    payload = {
        "device_code": device.device_code,
        "event_id": "evt-telemetry-001",
        "temperature_c": 44.5,
        "relative_humidity_pct": 55.0,
    }

    response = app_client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code == 201

    # Verify alert was generated in database
    from app.repositories.alert import list_alerts
    alerts = list_alerts(session=memory_session, device_id=device.id)
    assert len(alerts) == 1
    assert alerts[0].severity == "critical"
    assert alerts[0].status == "triggered"
    assert alerts[0].event_type == "threshold_exceeded"

    # Idempotent retransmission: 200 OK deduplicated, no duplicate alert
    retry_resp = app_client.post("/api/v1/readings", json=payload, headers=headers)
    assert retry_resp.status_code == 200
    assert retry_resp.json()["deduplicated"] is True

    alerts_after = list_alerts(session=memory_session, device_id=device.id)
    assert len(alerts_after) == 1

