"""Unit and integration tests for historical sensor readings, summaries, and time-range filtering."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.alert import Alert, AlertRule
from app.models.device import Device
from app.models.reading import SensorReading
from app.models.user import User
from app.models.worksite import Worksite
from app.repositories.alert import create_alert, create_alert_rule
from app.repositories.device import register_device
from app.repositories.reading import create_reading


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
        APP_NAME="HeatShield Test",
        APP_VERSION="0.1.0-test",
        APP_ENV="testing",
        DEBUG=True,
        API_PREFIX="/api/v1",
        DATABASE_URL=None,
    )
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: memory_session
    from app.core.user_auth import require_authenticated_user
    from app.models.user import User
    app.dependency_overrides[require_authenticated_user] = lambda: User(
        id=uuid.uuid4(), email="history-viewer@heatshield.gov.in", role="viewer", is_active=True
    )
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def sample_setup(memory_session: Session):
    """Seed sample worksite, devices, and readings for testing."""
    worksite = Worksite(
        id=uuid.uuid4(),
        name="Construction Site East",
        location_description="Jaipur Ring Road",
        is_active=True,
    )
    memory_session.add(worksite)
    memory_session.commit()

    device = register_device(
        session=memory_session,
        device_code="NODE-JP01-D001",
        worksite_id=worksite.id,
        display_name="Tower Crane Sensor",
        raw_token="raw-token-12345",
    )
    memory_session.commit()

    base_time = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)

    # Reading 1: 10:00 UTC - Valid 30.0 C, 50.0 %
    create_reading(
        session=memory_session,
        device_id=device.id,
        event_id="evt-001",
        measured_at=base_time,
        received_at=base_time + timedelta(seconds=2),
        temperature_c=Decimal("30.0"),
        relative_humidity_pct=Decimal("50.0"),
        quality_status="valid",
    )
    # Reading 2: 10:15 UTC - Valid 36.0 C, 60.0 %
    create_reading(
        session=memory_session,
        device_id=device.id,
        event_id="evt-002",
        measured_at=base_time + timedelta(minutes=15),
        received_at=base_time + timedelta(minutes=15, seconds=2),
        temperature_c=Decimal("36.0"),
        relative_humidity_pct=Decimal("60.0"),
        quality_status="valid",
    )
    # Reading 3: 10:30 UTC - Invalid reading (sensor glitch)
    create_reading(
        session=memory_session,
        device_id=device.id,
        event_id="evt-003",
        measured_at=base_time + timedelta(minutes=30),
        received_at=base_time + timedelta(minutes=30, seconds=2),
        temperature_c=Decimal("85.0"),
        relative_humidity_pct=Decimal("15.0"),
        quality_status="invalid",
    )
    # Reading 4: 10:45 UTC - Missing temperature (null)
    create_reading(
        session=memory_session,
        device_id=device.id,
        event_id="evt-004",
        measured_at=base_time + timedelta(minutes=45),
        received_at=base_time + timedelta(minutes=45, seconds=2),
        temperature_c=None,
        relative_humidity_pct=Decimal("55.0"),
        quality_status="missing",
    )
    memory_session.commit()

    return {
        "worksite": worksite,
        "device": device,
        "base_time": base_time,
    }


def test_history_query_valid_time_filters(app_client: TestClient, sample_setup):
    """GET /api/v1/readings/history returns readings within the time filter."""
    device = sample_setup["device"]
    base_time = sample_setup["base_time"]

    start = base_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (base_time + timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")

    response = app_client.get(
        "/api/v1/readings/history",
        params={"device_id": str(device.id), "start_time": start, "end_time": end},
    )
    assert response.status_code == 200
    payload = response.json()

    assert "data" in payload
    assert "pagination" in payload
    assert "summary" in payload
    assert "query" in payload

    # Should only return readings 1 and 2
    assert len(payload["data"]) == 2
    assert payload["pagination"]["total"] == 2
    assert payload["data"][0]["event_id"] == "evt-001"
    assert payload["data"][1]["event_id"] == "evt-002"
    assert payload["data"][0]["heat_index_c"] is not None


def test_history_invalid_date_range(app_client: TestClient, sample_setup):
    """GET /api/v1/readings/history returns 422 when start_time > end_time."""
    device = sample_setup["device"]
    base_time = sample_setup["base_time"]

    start = (base_time + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = base_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    response = app_client.get(
        "/api/v1/readings/history",
        params={"device_id": str(device.id), "start_time": start, "end_time": end},
    )
    assert response.status_code == 422
    err = response.json()
    assert "start_time must be less than or equal to end_time" in err["error"]["message"]


def test_history_exceeds_max_window(app_client: TestClient, sample_setup):
    """GET /api/v1/readings/history returns 422 when time range exceeds 30 days."""
    device = sample_setup["device"]
    base_time = sample_setup["base_time"]

    start = base_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (base_time + timedelta(days=35)).strftime("%Y-%m-%dT%H:%M:%SZ")

    response = app_client.get(
        "/api/v1/readings/history",
        params={"device_id": str(device.id), "start_time": start, "end_time": end},
    )
    assert response.status_code == 422
    err = response.json()
    assert "cannot exceed 30 days" in err["error"]["message"]


def test_history_pagination_limits(app_client: TestClient, sample_setup):
    """GET /api/v1/readings/history respects pagination limit and offset."""
    device = sample_setup["device"]
    base_time = sample_setup["base_time"]

    start = base_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (base_time + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Query with limit 2, offset 0
    resp1 = app_client.get(
        "/api/v1/readings/history",
        params={"device_id": str(device.id), "start_time": start, "end_time": end, "limit": 2, "offset": 0},
    )
    assert resp1.status_code == 200
    p1 = resp1.json()
    assert len(p1["data"]) == 2
    assert p1["pagination"]["total"] == 4
    assert p1["pagination"]["has_more"] is True
    assert p1["data"][0]["event_id"] == "evt-001"
    assert p1["data"][1]["event_id"] == "evt-002"

    # Query with limit 2, offset 2
    resp2 = app_client.get(
        "/api/v1/readings/history",
        params={"device_id": str(device.id), "start_time": start, "end_time": end, "limit": 2, "offset": 2},
    )
    assert resp2.status_code == 200
    p2 = resp2.json()
    assert len(p2["data"]) == 2
    assert p2["pagination"]["has_more"] is False
    assert p2["data"][0]["event_id"] == "evt-003"
    assert p2["data"][1]["event_id"] == "evt-004"


def test_history_deterministic_ordering(app_client: TestClient, sample_setup):
    """GET /api/v1/readings/history returns items in deterministic chronological order."""
    device = sample_setup["device"]
    base_time = sample_setup["base_time"]

    start = base_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (base_time + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Ascending order
    resp_asc = app_client.get(
        "/api/v1/readings/history",
        params={"device_id": str(device.id), "start_time": start, "end_time": end, "order_asc": "true"},
    )
    assert resp_asc.status_code == 200
    events_asc = [item["event_id"] for item in resp_asc.json()["data"]]
    assert events_asc == ["evt-001", "evt-002", "evt-003", "evt-004"]

    # Descending order
    resp_desc = app_client.get(
        "/api/v1/readings/history",
        params={"device_id": str(device.id), "start_time": start, "end_time": end, "order_asc": "false"},
    )
    assert resp_desc.status_code == 200
    events_desc = [item["event_id"] for item in resp_desc.json()["data"]]
    assert events_desc == ["evt-004", "evt-003", "evt-002", "evt-001"]


def test_history_summary_excludes_invalid_readings(app_client: TestClient, sample_setup):
    """Summary statistics correctly exclude invalid and missing readings."""
    device = sample_setup["device"]
    base_time = sample_setup["base_time"]

    start = base_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (base_time + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

    resp = app_client.get(
        "/api/v1/readings/history",
        params={"device_id": str(device.id), "start_time": start, "end_time": end},
    )
    assert resp.status_code == 200
    summary = resp.json()["summary"]

    assert summary["total_readings"] == 4
    assert summary["valid_readings"] == 2
    assert summary["invalid_readings"] == 1
    assert summary["missing_readings"] == 1

    # Only readings 1 (30.0 C) and 2 (36.0 C) are valid
    # 85.0 C from reading 3 MUST be excluded
    temp_stat = summary["temperature_c"]
    assert temp_stat["min"] == 30.0
    assert temp_stat["max"] == 36.0
    assert temp_stat["mean"] == 33.0

    # Only readings 1 (50.0 %) and 2 (60.0 %) are valid
    hum_stat = summary["relative_humidity_pct"]
    assert hum_stat["min"] == 50.0
    assert hum_stat["max"] == 60.0
    assert hum_stat["mean"] == 55.0

    # Heat index summary should be calculated from valid pairs
    hi_stat = summary["heat_index_c"]
    assert hi_stat["min"] is not None
    assert hi_stat["max"] is not None
    assert hi_stat["mean"] is not None


def test_history_summary_empty_when_no_readings(app_client: TestClient, sample_setup):
    """When no readings exist in the window, summary returns explicit nulls without false zeroes."""
    device = sample_setup["device"]

    start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    resp = app_client.get(
        "/api/v1/readings/history",
        params={"device_id": str(device.id), "start_time": start, "end_time": end},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["data"] == []
    assert payload["pagination"]["total"] == 0

    summary = payload["summary"]
    assert summary["total_readings"] == 0
    assert summary["valid_readings"] == 0
    assert summary["temperature_c"]["min"] is None
    assert summary["temperature_c"]["max"] is None
    assert summary["temperature_c"]["mean"] is None
    assert summary["relative_humidity_pct"]["min"] is None
    assert summary["heat_index_c"]["min"] is None


def test_alert_history_filtering_by_time_range(app_client: TestClient, memory_session: Session, sample_setup):
    """GET /api/v1/alerts supports filtering by start_time and end_time."""
    device = sample_setup["device"]
    base_time = sample_setup["base_time"]

    rule = create_alert_rule(
        session=memory_session,
        name="High Temp Trigger",
        metric="temperature_c",
        operator="gt",
        threshold_value=Decimal("35.0"),
        severity="warning",
        worksite_id=device.worksite_id,
    )
    memory_session.commit()

    # Alert 1 at base_time + 10m
    create_alert(
        session=memory_session,
        device_id=device.id,
        event_type="threshold_exceeded",
        severity="warning",
        status="triggered",
        alert_rule_id=rule.id,
        triggered_at=base_time + timedelta(minutes=10),
    )
    # Alert 2 at base_time + 50m
    create_alert(
        session=memory_session,
        device_id=device.id,
        event_type="threshold_exceeded",
        severity="critical",
        status="triggered",
        alert_rule_id=rule.id,
        triggered_at=base_time + timedelta(minutes=50),
    )
    memory_session.commit()

    user = User(
        email="viewer@heatshield.gov.in",
        display_name="Historical Viewer",
        password_hash="argon2id$mockhash",
        role="viewer",
        is_active=True,
    )
    memory_session.add(user)
    memory_session.commit()

    # Query alerts between base_time and base_time + 20m
    start = base_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (base_time + timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")

    resp = app_client.get(
        "/api/v1/alerts",
        params={"device_id": str(device.id), "start_time": start, "end_time": end},
        headers={"X-User-Id": str(user.id)},
    )
    assert resp.status_code == 200
    p = resp.json()
    assert p["pagination"]["total"] == 1
    assert len(p["data"]) == 1
    assert p["data"][0]["severity"] == "warning"

