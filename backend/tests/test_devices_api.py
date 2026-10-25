"""Unit and API integration tests for devices and latest readings endpoints."""

from datetime import datetime, timezone
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
from app.models.device import Device
from app.models.reading import SensorReading
from app.models.worksite import Worksite
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
        id=uuid.uuid4(), email="test@heatshield.gov.in", role="viewer", is_active=True
    )
    return TestClient(app, raise_server_exceptions=False)


def test_get_devices_empty_list(app_client: TestClient):
    """GET /api/v1/devices returns empty data array when no devices exist."""
    response = app_client.get("/api/v1/devices")
    assert response.status_code == 200
    payload = response.json()
    assert "data" in payload
    assert "pagination" in payload
    assert payload["data"] == []
    assert payload["pagination"]["total"] == 0
    assert payload["pagination"]["has_more"] is False


def test_get_devices_with_registered_devices(app_client: TestClient, memory_session: Session):
    """GET /api/v1/devices returns registered device data with correct fields."""
    worksite = Worksite(
        id=uuid.uuid4(),
        name="Dockyard Terminal A",
        location_description="Mumbai Port",
        is_active=True,
    )
    memory_session.add(worksite)
    memory_session.commit()

    device = register_device(
        session=memory_session,
        device_code="HS-MB01-D001",
        worksite_id=worksite.id,
        display_name="North Pier Sensor",
        firmware_version="0.2.1",
        raw_token="secret-token-test-1234",
    )
    memory_session.commit()

    response = app_client.get("/api/v1/devices")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert len(payload["data"]) == 1

    dev_data = payload["data"][0]
    assert dev_data["device_code"] == "HS-MB01-D001"
    assert dev_data["display_name"] == "North Pier Sensor"
    assert dev_data["status"] == "registered"
    assert dev_data["firmware_version"] == "0.2.1"
    assert dev_data["is_active"] is True
    # Confirm api_key_hash is NEVER exposed in API response
    assert "api_key_hash" not in dev_data
    assert "raw_token" not in dev_data


def test_get_latest_readings_empty(app_client: TestClient):
    """GET /api/v1/readings/latest returns empty data array when no readings exist."""
    response = app_client.get("/api/v1/readings/latest")
    assert response.status_code == 200
    payload = response.json()
    assert "data" in payload
    assert payload["data"] == []


def test_get_latest_readings_with_telemetry(app_client: TestClient, memory_session: Session):
    """GET /api/v1/readings/latest returns the most recent reading per device with device code."""
    worksite = Worksite(
        id=uuid.uuid4(),
        name="Steel Mill 3",
        location_description="Raipur",
        is_active=True,
    )
    memory_session.add(worksite)
    memory_session.commit()

    device = register_device(
        session=memory_session,
        device_code="HS-RP01-D001",
        worksite_id=worksite.id,
        display_name="Furnace Exit Node",
        raw_token="dev-token-999",
    )
    memory_session.commit()

    # Create older reading
    create_reading(
        session=memory_session,
        device_id=device.id,
        event_id="evt-001",
        measured_at=datetime(2026, 10, 25, 9, 0, 0, tzinfo=timezone.utc),
        received_at=datetime(2026, 10, 25, 9, 0, 2, tzinfo=timezone.utc),
        temperature_c=Decimal("35.0"),
        relative_humidity_pct=Decimal("50.0"),
    )
    # Create newer reading
    create_reading(
        session=memory_session,
        device_id=device.id,
        event_id="evt-002",
        measured_at=datetime(2026, 10, 25, 9, 15, 0, tzinfo=timezone.utc),
        received_at=datetime(2026, 10, 25, 9, 15, 2, tzinfo=timezone.utc),
        temperature_c=Decimal("38.5"),
        relative_humidity_pct=Decimal("65.0"),
    )
    memory_session.commit()

    response = app_client.get("/api/v1/readings/latest")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1

    item = payload["data"][0]
    assert item["device_code"] == "HS-RP01-D001"
    assert item["event_id"] == "evt-002"
    assert item["temperature_c"] == 38.5
    assert item["relative_humidity_pct"] == 65.0
    assert item["quality_status"] == "valid"
