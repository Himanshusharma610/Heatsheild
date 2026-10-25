"""Resilience, Error Handling, and Failure Modes Test Suite (Module 13).

Verifies system robustness and safe failure boundaries across:
1. Unauthorized & Unregistered IoT Devices (HTTP 401).
2. Conflicting retransmissions with identical event_id (HTTP 409 Conflict).
3. Payload validation and non-finite numbers (HTTP 422).
4. Out-of-bounds clock drift and physical boundary classification.
5. Inverted and excessive historical query ranges (HTTP 422).
6. Deactivated, malformed, or expired human user tokens (HTTP 401).
7. Safe empty-state behavior for latest readings, historical time series, and alerts.
8. Database persistence failure simulation returning HTTP 503 without false successes.
9. Non-existent resource identifiers safely returning HTTP 404.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.device import Device
from app.models.user import User
from app.models.worksite import Worksite
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
    """TestClient wired to isolated in-memory database."""
    settings = Settings(
        APP_NAME="HeatShield Resilience Test",
        APP_VERSION="0.1.0-resilience",
        APP_ENV="testing",
        DEBUG=True,
        API_PREFIX="/api/v1",
        DATABASE_URL=None,
    )
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: memory_session
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def test_setup(memory_session: Session) -> dict:
    """Provision baseline test fixtures."""
    worksite = Worksite(
        id=uuid.uuid4(),
        name="Tuticorin Heavy Logistics Yard",
        location_description="Port Zone C",
        is_active=True,
    )
    memory_session.add(worksite)
    memory_session.flush()

    raw_token = "device-psk-secret-tuticorin-001"
    device = Device(
        id=uuid.uuid4(),
        device_code="HS-TUT-D001",
        worksite_id=worksite.id,
        display_name="Yard Crane Sensor",
        status="online",
        api_key_hash=hash_device_token(raw_token),
        is_active=True,
    )
    memory_session.add(device)

    # Inactive/deactivated device
    deact_token = "device-psk-inactive-002"
    deactivated_device = Device(
        id=uuid.uuid4(),
        device_code="HS-TUT-DEACT",
        worksite_id=worksite.id,
        display_name="Decommissioned Sensor",
        status="offline",
        api_key_hash=hash_device_token(deact_token),
        is_active=False,
    )
    memory_session.add(deactivated_device)

    # Active viewer user
    viewer = create_user(
        session=memory_session,
        email="viewer.tuticorin@heatshield.gov.in",
        password_hash=hash_password("ViewerPass123!"),
        display_name="R. Meenakshi",
        role="viewer",
        is_active=True,
    )

    # Inactive user
    deactivated_user = create_user(
        session=memory_session,
        email="inactive.user@heatshield.gov.in",
        password_hash=hash_password("InactivePass123!"),
        display_name="Former Officer",
        role="supervisor",
        is_active=False,
    )
    memory_session.commit()

    return {
        "worksite": worksite,
        "device": device,
        "raw_token": raw_token,
        "deact_device": deactivated_device,
        "deact_token": deact_token,
        "viewer": viewer,
        "deact_user": deactivated_user,
    }


def auth_bearer(user: User) -> dict[str, str]:
    token, _ = create_access_token(user.id, user.email, user.role)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Device Authentication & Registration Failures
# ==============================================================================

def test_unregistered_device_code_rejected(app_client: TestClient, test_setup: dict):
    """Unknown device code must be rejected with HTTP 401 without revealing registration state."""
    payload = {
        "device_code": "HS-UNKNOWN-9999",
        "event_id": "evt-unreg-001",
        "temperature_c": 32.0,
        "relative_humidity_pct": 50.0,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = app_client.post("/api/v1/readings", json=payload, headers={"X-Device-Token": "some-token"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_device_token_rejected(app_client: TestClient, test_setup: dict):
    """Registered device with incorrect token must be rejected with HTTP 401."""
    device = test_setup["device"]
    payload = {
        "device_code": device.device_code,
        "event_id": "evt-badtoken-001",
        "temperature_c": 32.0,
        "relative_humidity_pct": 50.0,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = app_client.post("/api/v1/readings", json=payload, headers={"X-Device-Token": "wrong-secret-token"})
    assert resp.status_code == 401
    assert "Invalid device credentials" in resp.json()["error"]["message"]


def test_deactivated_device_rejected(app_client: TestClient, test_setup: dict):
    """Decommissioned/inactive device must be rejected with HTTP 401."""
    deact_device = test_setup["deact_device"]
    deact_token = test_setup["deact_token"]
    payload = {
        "device_code": deact_device.device_code,
        "event_id": "evt-deact-001",
        "temperature_c": 32.0,
        "relative_humidity_pct": 50.0,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = app_client.post("/api/v1/readings", json=payload, headers={"X-Device-Token": deact_token})
    assert resp.status_code == 401


def test_missing_device_token_header_rejected(app_client: TestClient, test_setup: dict):
    """Telemetry ingestion without auth headers must be rejected with HTTP 401."""
    device = test_setup["device"]
    payload = {
        "device_code": device.device_code,
        "event_id": "evt-noauth-001",
        "temperature_c": 32.0,
        "relative_humidity_pct": 50.0,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = app_client.post("/api/v1/readings", json=payload)
    assert resp.status_code == 401


# ==============================================================================
# 2. Conflicting Payload on Retransmission (Deduplication Safety)
# ==============================================================================

def test_conflicting_payload_duplicate_event_rejected(app_client: TestClient, test_setup: dict):
    """Same event_id with conflicting temperature data must be rejected with HTTP 409 Conflict."""
    device = test_setup["device"]
    raw_token = test_setup["raw_token"]
    headers = {"X-Device-Token": raw_token}

    event_id = "evt-conflict-test-001"
    now_time = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()

    # Initial ingestion
    p1 = {
        "device_code": device.device_code,
        "event_id": event_id,
        "temperature_c": 30.0,
        "relative_humidity_pct": 50.0,
        "measured_at": now_time,
    }
    resp1 = app_client.post("/api/v1/readings", json=p1, headers=headers)
    assert resp1.status_code == 201

    # Conflicting retransmission with different temperature
    p2 = {
        "device_code": device.device_code,
        "event_id": event_id,
        "temperature_c": 45.0,  # Conflict!
        "relative_humidity_pct": 50.0,
        "measured_at": now_time,
    }
    resp2 = app_client.post("/api/v1/readings", json=p2, headers=headers)
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "CONFLICT"
    assert "conflicting temperature" in resp2.json()["error"]["message"]


# ==============================================================================
# 3. Validation Failures and Non-Finite Numbers
# ==============================================================================

def test_invalid_payload_schema_and_types(app_client: TestClient, test_setup: dict):
    """Malformed payload or missing required fields must return HTTP 422."""
    raw_token = test_setup["raw_token"]
    headers = {"X-Device-Token": raw_token}

    # Missing event_id
    resp = app_client.post(
        "/api/v1/readings",
        json={"device_code": "HS-TUT-D001", "temperature_c": 30.0},
        headers=headers,
    )
    assert resp.status_code == 422


def test_non_finite_numbers_handling(app_client: TestClient, test_setup: dict):
    """String 'NaN' or infinity must not cause uncaught server exceptions."""
    raw_token = test_setup["raw_token"]
    headers = {"X-Device-Token": raw_token}

    resp = app_client.post(
        "/api/v1/readings",
        json={
            "device_code": "HS-TUT-D001",
            "event_id": "evt-nan-001",
            "temperature_c": "not-a-number",
            "measured_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    assert resp.status_code == 422


# ==============================================================================
# 4. Extreme Clock Drift and Physical Plausibility Tagging
# ==============================================================================

def test_extreme_future_clock_drift_classified_as_invalid(app_client: TestClient, test_setup: dict):
    """Telemetry with measurement time 48 hours in future must be classified as 'invalid'."""
    device = test_setup["device"]
    raw_token = test_setup["raw_token"]
    headers = {"X-Device-Token": raw_token}

    future_time = datetime.now(timezone.utc) + timedelta(hours=48)
    payload = {
        "device_code": device.device_code,
        "event_id": "evt-drift-future-001",
        "temperature_c": 33.0,
        "relative_humidity_pct": 55.0,
        "measured_at": future_time.isoformat(),
    }
    resp = app_client.post("/api/v1/readings", json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["data"]["quality_status"] == "invalid"


def test_extreme_temperature_out_of_physics_classified_as_invalid(app_client: TestClient, test_setup: dict):
    """Telemetry with extreme impossible temperature (+95 °C) must be classified as 'invalid'."""
    device = test_setup["device"]
    raw_token = test_setup["raw_token"]
    headers = {"X-Device-Token": raw_token}

    payload = {
        "device_code": device.device_code,
        "event_id": "evt-extreme-temp-001",
        "temperature_c": 95.0,  # Exceeds max plausible/extreme
        "relative_humidity_pct": 50.0,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = app_client.post("/api/v1/readings", json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["data"]["quality_status"] == "invalid"


# ==============================================================================
# 5. Historical Query Validation Errors
# ==============================================================================

def test_historical_time_range_inverted_rejected(app_client: TestClient, test_setup: dict):
    """Historical query with start_time > end_time must be rejected with HTTP 422."""
    viewer = test_setup["viewer"]
    viewer_headers = auth_bearer(viewer)

    start = "2026-10-25T14:00:00Z"
    end = "2026-10-25T10:00:00Z"

    resp = app_client.get(
        f"/api/v1/readings/history?start_time={start}&end_time={end}",
        headers=viewer_headers,
    )
    assert resp.status_code == 422
    assert "start_time must be less than or equal to end_time" in resp.json()["error"]["message"]


def test_historical_time_range_exceeding_30_days_rejected(app_client: TestClient, test_setup: dict):
    """Historical query exceeding 30-day window must be rejected with HTTP 422."""
    viewer = test_setup["viewer"]
    viewer_headers = auth_bearer(viewer)

    start = "2026-08-01T00:00:00Z"
    end = "2026-10-01T00:00:00Z"  # ~61 days

    resp = app_client.get(
        f"/api/v1/readings/history?start_time={start}&end_time={end}",
        headers=viewer_headers,
    )
    assert resp.status_code == 422
    assert "cannot exceed 30 days" in resp.json()["error"]["message"]


# ==============================================================================
# 6. User Authentication Failures
# ==============================================================================

def test_deactivated_user_token_rejected(app_client: TestClient, test_setup: dict):
    """Token belonging to a deactivated user must be rejected with HTTP 401."""
    deact_user = test_setup["deact_user"]
    deact_headers = auth_bearer(deact_user)

    resp = app_client.get("/api/v1/readings/latest", headers=deact_headers)
    assert resp.status_code == 401
    assert "User account is deactivated" in resp.json()["error"]["message"]


def test_corrupted_user_jwt_rejected(app_client: TestClient):
    """Malformed or invalid JWT must be rejected with HTTP 401."""
    resp = app_client.get(
        "/api/v1/readings/latest",
        headers={"Authorization": "Bearer not.a.valid.jwt.signature"},
    )
    assert resp.status_code == 401


# ==============================================================================
# 7. Safe Empty-Database Behavior
# ==============================================================================

def test_empty_database_responses_handled_gracefully(app_client: TestClient, test_setup: dict):
    """Queries on an empty database must return clean empty structures, never 500 crashes."""
    viewer = test_setup["viewer"]
    viewer_headers = auth_bearer(viewer)

    # Empty latest readings
    resp_latest = app_client.get("/api/v1/readings/latest", headers=viewer_headers)
    assert resp_latest.status_code == 200
    assert resp_latest.json()["data"] == []

    # Empty historical readings
    resp_hist = app_client.get("/api/v1/readings/history", headers=viewer_headers)
    assert resp_hist.status_code == 200
    assert resp_hist.json()["data"] == []
    assert resp_hist.json()["summary"]["total_readings"] == 0

    # Empty alerts
    resp_alerts = app_client.get("/api/v1/alerts", headers=viewer_headers)
    assert resp_alerts.status_code == 200
    assert resp_alerts.json()["data"] == []
    assert resp_alerts.json()["pagination"]["total"] == 0


# ==============================================================================
# 8. Database Persistence Failure Simulation (503 Service Unavailable)
# ==============================================================================

def test_database_persistence_failure_returns_503(app_client: TestClient, test_setup: dict):
    """Simulated database operational error during reading creation returns HTTP 503."""
    device = test_setup["device"]
    raw_token = test_setup["raw_token"]
    headers = {"X-Device-Token": raw_token}

    payload = {
        "device_code": device.device_code,
        "event_id": "evt-dberr-001",
        "temperature_c": 32.0,
        "relative_humidity_pct": 50.0,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }

    # Patch create_reading to simulate an unexpected database connection loss
    with patch("app.services.telemetry.create_reading", side_effect=OperationalError("Connection lost", {}, None)):
        resp = app_client.post("/api/v1/readings", json=payload, headers=headers)
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


# ==============================================================================
# 9. Non-Existent Resources Return HTTP 404
# ==============================================================================

def test_non_existent_alert_returns_404(app_client: TestClient, test_setup: dict):
    """Attempting to acknowledge or resolve a non-existent alert returns HTTP 404."""
    viewer = test_setup["viewer"]
    # Change viewer role in memory to supervisor for this check
    viewer.role = "supervisor"
    supervisor_headers = auth_bearer(viewer)

    non_existent_id = uuid.uuid4()
    resp = app_client.post(
        f"/api/v1/alerts/{non_existent_id}/acknowledge",
        json={"action_taken": "Testing non-existent alert"},
        headers=supervisor_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"
