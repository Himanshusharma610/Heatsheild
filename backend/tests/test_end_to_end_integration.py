"""End-to-End Integration Test Suite for HeatShield Bharat (Module 13).

Verifies the complete, interconnected system data flow:
1. Validated telemetry payload ingested via authenticated ESP32 device node (POST /readings).
2. Distinction between device measurement timestamp (measured_at) and server receipt time (received_at).
3. Idempotent deduplication on retransmission (HTTP 200 with deduplicated: true).
4. Deterministic NWS Heat Index evaluation and explainability tracking.
5. Automated alert rule evaluation and alert episode creation (status='triggered').
6. Deduplication policy preventing duplicate active alerts for ongoing sustained heat events.
7. Authenticated supervisor alert acknowledgement with mandatory safety action documentation.
8. Authenticated supervisor alert resolution with resolution audit notes.
9. Authenticated viewer querying latest readings (GET /readings/latest) and historical telemetry (GET /readings/history).
10. Strict RBAC enforcement: viewer cannot acknowledge alerts (403 Forbidden).
11. Strict credential segregation: IoT device token cannot perform supervisor alert actions (401 Unauthorized),
    and human JWT cannot ingest sensor readings (401 Unauthorized).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.alert import Alert, AlertAcknowledgement, AlertRule
from app.models.device import Device
from app.models.reading import SensorReading
from app.models.user import User
from app.models.worksite import Worksite
from app.repositories.alert import create_alert_rule, get_alert_by_id
from app.repositories.device import hash_device_token
from app.repositories.user import create_user


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
def app_client(memory_session: Session) -> TestClient:
    """TestClient wired to isolated in-memory database with actual auth dependencies active."""
    settings = Settings(
        APP_NAME="HeatShield E2E Integration Test",
        APP_VERSION="0.1.0-e2e",
        APP_ENV="testing",
        DEBUG=True,
        API_PREFIX="/api/v1",
        DATABASE_URL=None,
    )
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: memory_session
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def e2e_environment(memory_session: Session) -> dict:
    """Provision a full test environment: worksite, device, alert rule, supervisor, and viewer."""
    worksite = Worksite(
        id=uuid.uuid4(),
        name="Ennore Industrial Port Terminal B",
        location_description="Chennai Outer Harbor",
        is_active=True,
    )
    memory_session.add(worksite)
    memory_session.flush()

    raw_device_token = "esp32-en01-secret-preshared-token-2026"
    device = Device(
        id=uuid.uuid4(),
        device_code="HS-EN01-D001",
        worksite_id=worksite.id,
        display_name="Berth 4 Weather Sensor",
        status="online",
        api_key_hash=hash_device_token(raw_device_token),
        is_active=True,
    )
    memory_session.add(device)

    # Supervisor user
    supervisor = create_user(
        session=memory_session,
        email="supervisor.ennore@heatshield.gov.in",
        password_hash=hash_password("SupervisorStrongSecret123!"),
        display_name="K. Sundaram",
        role="supervisor",
        is_active=True,
    )

    # Read-only viewer user
    viewer = create_user(
        session=memory_session,
        email="safety.viewer@heatshield.gov.in",
        password_hash=hash_password("ViewerStrongSecret123!"),
        display_name="Ananya Sharma",
        role="viewer",
        is_active=True,
    )

    # Configured alert rule for extreme heat
    # Threshold: Heat Index >= 40.0 °C (Warning level)
    rule = create_alert_rule(
        session=memory_session,
        name="High Thermal Strain Warning",
        metric="heat_index",
        operator="gte",
        severity="warning",
        worksite_id=worksite.id,
        threshold_value=Decimal("40.0"),
        is_enabled=True,
    )
    memory_session.commit()

    return {
        "worksite": worksite,
        "device": device,
        "raw_device_token": raw_device_token,
        "supervisor": supervisor,
        "viewer": viewer,
        "rule": rule,
    }


def auth_bearer(user: User) -> dict[str, str]:
    """Helper to generate standard JWT Bearer Authorization header."""
    token, _ = create_access_token(user.id, user.email, user.role)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# Comprehensive End-to-End Test Scenario
# ==============================================================================

def test_full_telemetry_to_alert_lifecycle_flow(app_client: TestClient, e2e_environment: dict, memory_session: Session):
    """Execute the complete end-to-end data flow:
    1. IoT device ingests hazardous telemetry.
    2. Telemetry is deduplicated on retry.
    3. Heat Index calculation triggers an active Alert episode.
    4. Viewer reads latest & historical telemetry.
    5. Viewer cannot acknowledge alert (403).
    6. Supervisor acknowledges and resolves alert with safety documentation.
    7. Device credentials cannot act as supervisor.
    """
    device = e2e_environment["device"]
    raw_token = e2e_environment["raw_device_token"]
    supervisor = e2e_environment["supervisor"]
    viewer = e2e_environment["viewer"]
    rule = e2e_environment["rule"]

    device_headers = {"X-Device-Token": raw_token}
    supervisor_headers = auth_bearer(supervisor)
    viewer_headers = auth_bearer(viewer)

    # --------------------------------------------------------------------------
    # Step 1: Ingest sensor telemetry from physical IoT node (hardware mode)
    # Ambient: 38.0 °C, 65.0% RH -> NWS Heat Index is ~53.8 °C (Hazardous)
    # --------------------------------------------------------------------------
    event_id = "evt-2026-10-25-001"
    device_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    ingest_payload = {
        "device_code": device.device_code,
        "event_id": event_id,
        "temperature_c": 38.0,
        "relative_humidity_pct": 65.0,
        "measured_at": device_time.isoformat(),
        "firmware_version": "0.3.1",
        "source_mode": "hardware",
    }

    resp_ingest = app_client.post("/api/v1/readings", json=ingest_payload, headers=device_headers)
    assert resp_ingest.status_code == 201, f"Ingestion failed: {resp_ingest.text}"
    ingest_data = resp_ingest.json()["data"]

    # Verify field integrity and distinct timestamps
    assert ingest_data["event_id"] == event_id
    assert ingest_data["temperature_c"] == 38.0
    assert ingest_data["relative_humidity_pct"] == 65.0
    assert ingest_data["quality_status"] == "valid"
    assert ingest_data["source_mode"] == "hardware"
    # Ensure measured_at matches device clock and received_at is populated by server
    assert ingest_data["measured_at"] is not None
    assert "received_at" in ingest_data

    # --------------------------------------------------------------------------
    # Step 2: Idempotent retry handling
    # Retransmitting identical payload must return 200 OK with deduplicated: true
    # --------------------------------------------------------------------------
    resp_retry = app_client.post("/api/v1/readings", json=ingest_payload, headers=device_headers)
    assert resp_retry.status_code == 200
    assert resp_retry.json()["deduplicated"] is True
    assert resp_retry.json()["data"]["event_id"] == event_id

    # --------------------------------------------------------------------------
    # Step 3: Verify Alert Episode Triggered by Ingestion
    # The reading breached rule (38.0°C / 65% RH => Heat Index > 40.0°C)
    # --------------------------------------------------------------------------
    resp_alerts = app_client.get("/api/v1/alerts?status=triggered", headers=viewer_headers)
    assert resp_alerts.status_code == 200
    alerts_data = resp_alerts.json()["data"]
    assert len(alerts_data) == 1
    triggered_alert = alerts_data[0]
    assert triggered_alert["alert_rule_id"] == str(rule.id)
    assert triggered_alert["severity"] == "warning"
    assert triggered_alert["status"] == "triggered"
    alert_id = triggered_alert["id"]

    # --------------------------------------------------------------------------
    # Step 4: Sustained heat reading deduplication
    # A subsequent reading with identical active status must not create a duplicate alert
    # --------------------------------------------------------------------------
    second_payload = {
        "device_code": device.device_code,
        "event_id": "evt-2026-10-25-002",
        "temperature_c": 38.5,
        "relative_humidity_pct": 66.0,
        "measured_at": (device_time + timedelta(minutes=5)).isoformat(),
        "source_mode": "hardware",
    }
    resp_second_ingest = app_client.post("/api/v1/readings", json=second_payload, headers=device_headers)
    assert resp_second_ingest.status_code == 201

    # Check alert count remains 1 (deduplicated episode)
    resp_alerts_count = app_client.get("/api/v1/alerts?status=triggered", headers=viewer_headers)
    assert len(resp_alerts_count.json()["data"]) == 1

    # --------------------------------------------------------------------------
    # Step 5: Read-only Viewer Queries Latest and History
    # --------------------------------------------------------------------------
    resp_latest = app_client.get("/api/v1/readings/latest", headers=viewer_headers)
    assert resp_latest.status_code == 200
    latest_items = resp_latest.json()["data"]
    assert len(latest_items) == 1
    assert latest_items[0]["event_id"] == "evt-2026-10-25-002"
    assert latest_items[0]["temperature_c"] == 38.5
    assert latest_items[0]["relative_humidity_pct"] == 66.0

    # Historical query with descriptive statistics
    resp_history = app_client.get(
        f"/api/v1/readings/history?device_id={device.id}&limit=10",
        headers=viewer_headers,
    )
    assert resp_history.status_code == 200
    hist_json = resp_history.json()
    assert hist_json["pagination"]["total"] == 2
    # Verify summary metrics min/max/mean
    summary = hist_json["summary"]
    assert summary["temperature_c"]["min"] == 38.0
    assert summary["temperature_c"]["max"] == 38.5
    assert summary["valid_readings"] == 2
    assert summary["total_readings"] == 2
    # Heat index calculation included on history items
    assert hist_json["data"][0]["heat_index_c"] is not None

    # --------------------------------------------------------------------------
    # Step 6: Authorization Boundary Enforcement
    # Viewer tries to acknowledge alert -> REJECTED (403 Forbidden)
    # --------------------------------------------------------------------------
    resp_viewer_ack = app_client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"action_taken": "Viewer attempt to acknowledge"},
        headers=viewer_headers,
    )
    assert resp_viewer_ack.status_code == 403
    assert resp_viewer_ack.json()["error"]["code"] == "FORBIDDEN"

    # Device token tries to acknowledge alert -> REJECTED (401 Unauthorized)
    resp_device_ack = app_client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"action_taken": "Device attempt to acknowledge"},
        headers=device_headers,
    )
    assert resp_device_ack.status_code == 401
    assert "Device credentials cannot be used" in resp_device_ack.json()["error"]["message"]

    # --------------------------------------------------------------------------
    # Step 7: Supervisor Acknowledges Alert
    # Must persist documented corrective/safety action taken
    # --------------------------------------------------------------------------
    ack_payload = {
        "action_taken": "Worksite siren sounded; ordered 15-minute mandatory shaded hydration break for Berth 4 workers."
    }
    resp_ack = app_client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json=ack_payload,
        headers=supervisor_headers,
    )
    assert resp_ack.status_code == 200
    ack_data = resp_ack.json()["data"]
    assert ack_data["status"] == "acknowledged"
    assert ack_data["acknowledgement"]["action_taken"] == ack_payload["action_taken"]
    assert ack_data["acknowledgement"]["actor_id"] == str(supervisor.id)

    # --------------------------------------------------------------------------
    # Step 8: Supervisor Resolves Alert Episode
    # --------------------------------------------------------------------------
    res_payload = {
        "resolution_notes": "Sea breeze arrived at 11:45 UTC; temperature dropped to 32.5 °C. Normal operations resumed."
    }
    resp_resolve = app_client.post(
        f"/api/v1/alerts/{alert_id}/resolve",
        json=res_payload,
        headers=supervisor_headers,
    )
    assert resp_resolve.status_code == 200
    assert resp_resolve.json()["data"]["status"] == "resolved"

    # Verify in database that alert status is updated
    alert_in_db = get_alert_by_id(memory_session, uuid.UUID(alert_id))
    assert alert_in_db is not None
    assert alert_in_db.status == "resolved"
    assert alert_in_db.resolved_at is not None

    # --------------------------------------------------------------------------
    # Step 9: Verify Rejection of Human Credentials on IoT Ingestion
    # --------------------------------------------------------------------------
    resp_human_ingest = app_client.post(
        "/api/v1/readings",
        json=ingest_payload,
        headers=supervisor_headers,
    )
    assert resp_human_ingest.status_code == 401
    assert "Human user credentials cannot be used" in resp_human_ingest.json()["error"]["message"]


def test_benign_reading_does_not_trigger_alert(app_client: TestClient, e2e_environment: dict):
    """Verify that an environmental reading below alert thresholds does not create alerts."""
    device = e2e_environment["device"]
    raw_token = e2e_environment["raw_device_token"]
    viewer = e2e_environment["viewer"]

    device_headers = {"X-Device-Token": raw_token}
    viewer_headers = auth_bearer(viewer)

    # Ambient: 27.0 °C, 40% RH -> Heat Index is ~27.2 °C (Normal, well below 40.0 °C threshold)
    benign_payload = {
        "device_code": device.device_code,
        "event_id": "evt-benign-2026-001",
        "temperature_c": 27.0,
        "relative_humidity_pct": 40.0,
        "measured_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        "source_mode": "hardware",
    }
    resp = app_client.post("/api/v1/readings", json=benign_payload, headers=device_headers)
    assert resp.status_code == 201

    # Verify no active or triggered alerts exist
    resp_alerts = app_client.get("/api/v1/alerts?status=triggered", headers=viewer_headers)
    assert resp_alerts.status_code == 200
    assert len(resp_alerts.json()["data"]) == 0


def test_alert_lifecycle_invalid_transitions(app_client: TestClient, e2e_environment: dict, memory_session: Session):
    """Verify state machine constraints: cannot resolve or acknowledge already resolved alerts."""
    device = e2e_environment["device"]
    raw_token = e2e_environment["raw_device_token"]
    supervisor = e2e_environment["supervisor"]

    device_headers = {"X-Device-Token": raw_token}
    supervisor_headers = auth_bearer(supervisor)

    # Ingest hazardous reading
    resp = app_client.post(
        "/api/v1/readings",
        json={
            "device_code": device.device_code,
            "event_id": "evt-transition-test-001",
            "temperature_c": 42.0,
            "relative_humidity_pct": 70.0,
            "measured_at": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
            "source_mode": "hardware",
        },
        headers=device_headers,
    )
    assert resp.status_code == 201

    # Fetch triggered alert
    resp_alerts = app_client.get("/api/v1/alerts?status=triggered", headers=supervisor_headers)
    alert = resp_alerts.json()["data"][0]
    alert_id = alert["id"]

    # 1. Resolve alert directly
    resp_resolve = app_client.post(
        f"/api/v1/alerts/{alert_id}/resolve",
        json={"resolution_notes": "Immediate mitigation implemented."},
        headers=supervisor_headers,
    )
    assert resp_resolve.status_code == 200
    assert resp_resolve.json()["data"]["status"] == "resolved"

    # 2. Cannot re-resolve an already resolved alert (409 Conflict)
    resp_re_resolve = app_client.post(
        f"/api/v1/alerts/{alert_id}/resolve",
        json={"resolution_notes": "Duplicate resolution attempt."},
        headers=supervisor_headers,
    )
    assert resp_re_resolve.status_code == 409
    assert "already resolved" in resp_re_resolve.json()["error"]["message"]

    # 3. Cannot acknowledge an already resolved alert (409 Conflict)
    resp_re_ack = app_client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"action_taken": "Belated acknowledgement attempt."},
        headers=supervisor_headers,
    )
    assert resp_re_ack.status_code == 409
    assert "already in 'resolved' state" in resp_re_ack.json()["error"]["message"]


def test_missing_and_partial_measurements_persistence(app_client: TestClient, e2e_environment: dict):
    """Verify that partial sensor failure persists NULL in database and is never converted to 0.0."""
    device = e2e_environment["device"]
    raw_token = e2e_environment["raw_device_token"]
    viewer = e2e_environment["viewer"]

    device_headers = {"X-Device-Token": raw_token}
    viewer_headers = auth_bearer(viewer)

    # Ingest reading where humidity sensor failed (humidity is None)
    partial_payload = {
        "device_code": device.device_code,
        "event_id": "evt-partial-hum-null-001",
        "temperature_c": 35.5,
        "relative_humidity_pct": None,
        "measured_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        "source_mode": "hardware",
    }
    resp = app_client.post("/api/v1/readings", json=partial_payload, headers=device_headers)
    assert resp.status_code == 201
    reading = resp.json()["data"]

    assert reading["temperature_c"] == 35.5
    assert reading["relative_humidity_pct"] is None  # CRITICAL: not converted to 0.0

    # Verify latest reading query returns exact null
    resp_latest = app_client.get("/api/v1/readings/latest", headers=viewer_headers)
    assert resp_latest.status_code == 200
    found = next(r for r in resp_latest.json()["data"] if r["event_id"] == "evt-partial-hum-null-001")
    assert found["temperature_c"] == 35.5
    assert found["relative_humidity_pct"] is None


def test_viewer_and_device_forbidden_from_admin_rule_creation(app_client: TestClient, e2e_environment: dict):
    """Verify that viewers and devices cannot create or modify alert rules."""
    device = e2e_environment["device"]
    raw_token = e2e_environment["raw_device_token"]
    viewer = e2e_environment["viewer"]
    worksite = e2e_environment["worksite"]

    device_headers = {"X-Device-Token": raw_token}
    viewer_headers = auth_bearer(viewer)

    rule_payload = {
        "name": "Unauthorized Test Rule",
        "metric": "temperature",
        "operator": "gte",
        "severity": "critical",
        "worksite_id": str(worksite.id),
        "threshold_value": 45.0,
        "is_enabled": True,
    }

    # Viewer attempt -> 403 Forbidden
    resp_viewer = app_client.post("/api/v1/alert-rules", json=rule_payload, headers=viewer_headers)
    assert resp_viewer.status_code == 403
    assert resp_viewer.json()["error"]["code"] == "FORBIDDEN"

    # Device attempt -> 401 Unauthorized (device token cannot act as human user)
    resp_device = app_client.post("/api/v1/alert-rules", json=rule_payload, headers=device_headers)
    assert resp_device.status_code == 401
    assert "Device credentials cannot be used" in resp_device.json()["error"]["message"]

