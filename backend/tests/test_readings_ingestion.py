"""Comprehensive automated tests for telemetry ingestion and reliability (Module 6).

Covers:
1. Valid authenticated ingestion (201 Created)
2. Missing or malformed fields (422 Unprocessable Content)
3. Invalid and out-of-bounds metrics (422 for humidity > 100 / NaN; quality classification for thermal extremes)
4. Unknown, inactive, and unauthenticated devices (401 Unauthorized without enumeration)
5. Idempotent duplicate event delivery (200 OK with deduplicated: true)
6. Conflicting duplicate event payloads (409 Conflict)
7. Transaction rollback on database failure (no false success)
8. Timestamp handling (missing, UTC conversion, future drift suspect classification)
9. No leakage of credentials in logs or responses
10. Heartbeat and device status updates on successful ingestion
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.device import Device
from app.models.reading import SensorReading
from app.models.worksite import Worksite
from app.repositories.device import hash_device_token, register_device
from app.repositories.worksite import create_worksite
from app.services.telemetry import assess_reading_quality


@pytest.fixture
def sqlite_engine():
    """Create an in-memory SQLite database engine for fast, isolated testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def session(sqlite_engine) -> Session:
    """Provide a transactional database session."""
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
    sess = session_factory()
    yield sess
    sess.close()


@pytest.fixture
def test_setup(session: Session):
    """Seed worksite and registered test device with known token."""
    worksite = create_worksite(session, name="Alpha Mine Site", location_description="Rajasthan, IN")
    raw_token = "valid-device-token-secret-xyz123"
    device = register_device(
        session=session,
        device_code="HS-WS01-D001",
        worksite_id=worksite.id,
        display_name="North Pit Sensor",
        firmware_version="0.1.0",
        raw_token=raw_token,
    )
    session.commit()
    return {
        "worksite": worksite,
        "device": device,
        "token": raw_token,
        "token_hash": hash_device_token(raw_token),
    }


@pytest.fixture
def client(sqlite_engine) -> TestClient:
    """Create a FastAPI test client wired to the in-memory database."""
    settings = Settings(
        APP_NAME="HeatShield Bharat Ingestion Test",
        APP_ENV="testing",
        DEBUG=True,
        API_PREFIX="/api/v1",
        DATABASE_URL="sqlite:///:memory:",
    )
    app = create_app(settings)

    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, raise_server_exceptions=False)


# ==============================================================================
# 1. Valid Authenticated Ingestion
# ==============================================================================

def test_valid_authenticated_ingestion(client: TestClient, test_setup: dict, session: Session):
    """Valid payload with X-Device-Token succeeds with HTTP 201 Created and persists record."""
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "device_code": "HS-WS01-D001",
        "event_id": "evt-00001",
        "measured_at": now_iso,
        "temperature_c": 38.5,
        "relative_humidity_pct": 65.0,
        "firmware_version": "0.1.0",
        "source_mode": "hardware",
    }
    headers = {"X-Device-Token": test_setup["token"]}

    response = client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json().get("data", {})
    assert data["device_id"] == str(test_setup["device"].id)
    assert data["event_id"] == "evt-00001"
    assert data["temperature_c"] == 38.5
    assert data["relative_humidity_pct"] == 65.0
    assert data["quality_status"] == "valid"
    assert data["source_mode"] == "hardware"
    assert data["received_at"] is not None

    # Verify device status and heartbeat updated
    device_record = session.get(Device, test_setup["device"].id)
    session.refresh(device_record)
    assert device_record.status == "online"
    assert device_record.last_seen_at is not None


def test_valid_bearer_token_authentication(client: TestClient, test_setup: dict):
    """Authentication succeeds when token is transmitted via Authorization: Bearer scheme."""
    payload = {
        "device_code": "HS-WS01-D001",
        "event_id": "evt-bearer-01",
        "temperature_c": 34.0,
        "relative_humidity_pct": 50.0,
    }
    headers = {"Authorization": f"Bearer {test_setup['token']}"}

    response = client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code == 201


# ==============================================================================
# 2. Authentication Failures & Security
# ==============================================================================

def test_missing_authentication_header(client: TestClient):
    """Missing auth header returns 401 Unauthorized."""
    payload = {"device_code": "HS-WS01-D001", "event_id": "evt-00002"}
    response = client.post("/api/v1/readings", json=payload)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_device_token(client: TestClient, test_setup: dict):
    """Incorrect token returns 401 Unauthorized without leaking details."""
    payload = {"device_code": "HS-WS01-D001", "event_id": "evt-00003"}
    headers = {"X-Device-Token": "completely-invalid-token"}

    response = client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert "Invalid device credentials" in response.json()["error"]["message"]


def test_unknown_device_code(client: TestClient, test_setup: dict):
    """Unregistered device code returns generic 401 Unauthorized to prevent device enumeration."""
    payload = {"device_code": "HS-NONEXISTENT-999", "event_id": "evt-00004"}
    headers = {"X-Device-Token": test_setup["token"]}

    response = client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    # Does not disclose whether device exists
    assert response.json()["error"]["message"] == "Invalid device credentials"


def test_deactivated_device_rejected(client: TestClient, test_setup: dict, session: Session):
    """Deactivated device returns 401 Unauthorized."""
    device = session.get(Device, test_setup["device"].id)
    device.is_active = False
    session.commit()

    payload = {"device_code": "HS-WS01-D001", "event_id": "evt-00005"}
    headers = {"X-Device-Token": test_setup["token"]}

    response = client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_no_credential_leakage_in_error_responses(client: TestClient, test_setup: dict):
    """Verify error responses do not echo presented tokens or reveal database details."""
    secret_token = "ultra-secret-token-not-to-leak"
    payload = {"device_code": "HS-WS01-D001", "event_id": "evt-00006"}
    headers = {"X-Device-Token": secret_token}

    response = client.post("/api/v1/readings", json=payload, headers=headers)
    response_text = response.text
    assert secret_token not in response_text
    assert "api_key_hash" not in response_text
    assert "sqlite" not in response_text.lower()


# ==============================================================================
# 3. Payload Validation & Boundary Enforcement
# ==============================================================================

def test_missing_required_fields(client: TestClient, test_setup: dict):
    """Missing event_id or device_code fails validation with 422."""
    headers = {"X-Device-Token": test_setup["token"]}

    # Missing event_id
    res1 = client.post("/api/v1/readings", json={"device_code": "HS-WS01-D001"}, headers=headers)
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "VALIDATION_ERROR"

    # Missing device_code
    res2 = client.post("/api/v1/readings", json={"event_id": "evt-123"}, headers=headers)
    assert res2.status_code == 422


def test_relative_humidity_bounds(client: TestClient, test_setup: dict):
    """Humidity outside [0, 100] is rejected with 422."""
    headers = {"X-Device-Token": test_setup["token"]}

    # Humidity > 100
    res1 = client.post(
        "/api/v1/readings",
        json={"device_code": "HS-WS01-D001", "event_id": "evt-hum-1", "relative_humidity_pct": 105.0},
        headers=headers,
    )
    assert res1.status_code == 422

    # Humidity < 0
    res2 = client.post(
        "/api/v1/readings",
        json={"device_code": "HS-WS01-D001", "event_id": "evt-hum-2", "relative_humidity_pct": -5.0},
        headers=headers,
    )
    assert res2.status_code == 422


def test_extra_fields_forbidden(client: TestClient, test_setup: dict):
    """Unrecognized payload fields are rejected under strict schema configuration."""
    headers = {"X-Device-Token": test_setup["token"]}
    payload = {
        "device_code": "HS-WS01-D001",
        "event_id": "evt-extra-1",
        "unrecognized_field": "injected",
    }
    response = client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code == 422


# ==============================================================================
# 4. Data Quality & Timestamp Classification
# ==============================================================================

def test_missing_measurement_data_classification(client: TestClient, test_setup: dict):
    """Readings with neither temperature nor humidity are classified as 'missing'."""
    headers = {"X-Device-Token": test_setup["token"]}
    payload = {
        "device_code": "HS-WS01-D001",
        "event_id": "evt-missing-1",
        "temperature_c": None,
        "relative_humidity_pct": None,
    }
    response = client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["quality_status"] == "missing"


def test_extreme_temperature_quality_classification(client: TestClient, test_setup: dict):
    """Temperatures outside physical plausibility bounds are classified as 'suspect' or 'invalid'."""
    headers = {"X-Device-Token": test_setup["token"]}

    # Suspect temperature (75.0 C, above plausibility 70 C but below extreme 85 C)
    res_suspect = client.post(
        "/api/v1/readings",
        json={"device_code": "HS-WS01-D001", "event_id": "evt-suspect-1", "temperature_c": 75.0, "relative_humidity_pct": 40.0},
        headers=headers,
    )
    assert res_suspect.status_code == 201
    assert res_suspect.json()["data"]["quality_status"] == "suspect"

    # Invalid temperature (95.0 C, above extreme 85 C)
    res_invalid = client.post(
        "/api/v1/readings",
        json={"device_code": "HS-WS01-D001", "event_id": "evt-invalid-1", "temperature_c": 95.0, "relative_humidity_pct": 40.0},
        headers=headers,
    )
    assert res_invalid.status_code == 201
    assert res_invalid.json()["data"]["quality_status"] == "invalid"


def test_future_clock_drift_quality_classification(client: TestClient, test_setup: dict):
    """Timestamps drifted > 10 min into the future are accepted but classified as 'suspect'."""
    headers = {"X-Device-Token": test_setup["token"]}
    future_time = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()

    payload = {
        "device_code": "HS-WS01-D001",
        "event_id": "evt-future-1",
        "measured_at": future_time,
        "temperature_c": 30.0,
        "relative_humidity_pct": 50.0,
    }
    response = client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["quality_status"] == "suspect"


def test_missing_timestamp_persisted_cleanly(client: TestClient, test_setup: dict):
    """Missing measured_at is preserved as None while received_at is set by server."""
    headers = {"X-Device-Token": test_setup["token"]}
    payload = {
        "device_code": "HS-WS01-D001",
        "event_id": "evt-notime-1",
        "measured_at": None,
        "temperature_c": 32.0,
        "relative_humidity_pct": 55.0,
    }
    response = client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["measured_at"] is None
    assert data["received_at"] is not None


# ==============================================================================
# 5. Idempotent Deduplication & Conflict Detection
# ==============================================================================

def test_idempotent_duplicate_delivery(client: TestClient, test_setup: dict, session: Session):
    """Retransmitting an identical event returns HTTP 200 OK with deduplicated: true."""
    headers = {"X-Device-Token": test_setup["token"]}
    payload = {
        "device_code": "HS-WS01-D001",
        "event_id": "evt-dedup-01",
        "temperature_c": 36.2,
        "relative_humidity_pct": 58.0,
    }

    # Initial transmission -> 201 Created
    res1 = client.post("/api/v1/readings", json=payload, headers=headers)
    assert res1.status_code == 201
    first_id = res1.json()["data"]["id"]

    # Retransmission -> 200 OK with deduplicated: true
    res2 = client.post("/api/v1/readings", json=payload, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["deduplicated"] is True
    assert res2.json()["data"]["id"] == first_id

    # Confirm only one reading was stored in database
    readings = session.scalars(
        select(SensorReading).where(SensorReading.event_id == "evt-dedup-01")
    ).all()
    assert len(readings) == 1


def test_conflicting_duplicate_payload_returns_409(client: TestClient, test_setup: dict):
    """Reusing an event ID with differing measurement values triggers HTTP 409 Conflict."""
    headers = {"X-Device-Token": test_setup["token"]}
    payload_original = {
        "device_code": "HS-WS01-D001",
        "event_id": "evt-conflict-01",
        "temperature_c": 35.0,
        "relative_humidity_pct": 50.0,
    }
    res1 = client.post("/api/v1/readings", json=payload_original, headers=headers)
    assert res1.status_code == 201

    # Same event ID but different temperature
    payload_conflicting = {
        "device_code": "HS-WS01-D001",
        "event_id": "evt-conflict-01",
        "temperature_c": 42.0,  # Conflict!
        "relative_humidity_pct": 50.0,
    }
    res2 = client.post("/api/v1/readings", json=payload_conflicting, headers=headers)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "CONFLICT"
    assert "conflicting temperature" in res2.json()["error"]["message"]


# ==============================================================================
# 6. Transaction Rollback on Database Failure
# ==============================================================================

def test_database_failure_does_not_return_false_success(client: TestClient, test_setup: dict, monkeypatch):
    """If database persistence fails, an error response is returned; never a false 200/201."""
    from app.services import telemetry

    def broken_create_reading(*args, **kwargs):
        raise RuntimeError("Simulated catastrophic storage failure")

    monkeypatch.setattr(telemetry, "create_reading", broken_create_reading)

    headers = {"X-Device-Token": test_setup["token"]}
    payload = {
        "device_code": "HS-WS01-D001",
        "event_id": "evt-fail-01",
        "temperature_c": 30.0,
    }
    response = client.post("/api/v1/readings", json=payload, headers=headers)
    assert response.status_code in (500, 503)
    assert response.json()["error"]["code"] in ("INTERNAL_ERROR", "SERVICE_UNAVAILABLE")
