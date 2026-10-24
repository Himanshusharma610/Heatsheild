"""Unit tests for database readiness probe integration."""

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app


def test_ready_endpoint_database_not_configured() -> None:
    """Verify GET /ready reports database as not_configured when DATABASE_URL is None."""
    settings = Settings(
        DATABASE_URL=None,
        APP_ENV="testing",
        SECRET_KEY=SecretStr("readiness-test-secret"),
    )
    app = create_app(settings)
    client = TestClient(app)

    response = client.get("/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert data["services"]["api"] == "ready"
    assert data["services"]["database"] == "not_configured"


def test_ready_endpoint_database_connected(monkeypatch) -> None:
    """Verify GET /ready reports database as connected when connectivity check succeeds."""
    settings = Settings(
        DATABASE_URL="postgresql://test_user:test_pw@localhost:5432/test_db",
        APP_ENV="testing",
        SECRET_KEY=SecretStr("readiness-test-secret"),
    )
    app = create_app(settings)

    # Mock check_db_connectivity to return True
    monkeypatch.setattr("app.api.health.check_db_connectivity", lambda: (True, None))

    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert data["services"]["api"] == "ready"
    assert data["services"]["database"] == "connected"


def test_ready_endpoint_database_unavailable(monkeypatch) -> None:
    """Verify GET /ready reports 503 and not_ready when database connectivity fails."""
    settings = Settings(
        DATABASE_URL="postgresql://test_user:super_secret_db_password@localhost:5432/test_db",
        APP_ENV="testing",
        SECRET_KEY=SecretStr("readiness-test-secret"),
    )
    app = create_app(settings)

    # Mock check_db_connectivity to return False
    monkeypatch.setattr(
        "app.api.health.check_db_connectivity",
        lambda: (False, "Database connection failed"),
    )

    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 503

    data = response.json()
    assert data["status"] == "not_ready"
    assert data["services"]["api"] == "ready"
    assert data["services"]["database"] == "unavailable"

    # Crucial security check: sensitive credentials must not leak
    assert "super_secret_db_password" not in response.text


def test_liveness_probe_independent_of_database_outage(monkeypatch) -> None:
    """Verify GET /health remains 200 healthy even when database is unavailable (liveness independence)."""
    settings = Settings(
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
        APP_ENV="testing",
        SECRET_KEY=SecretStr("readiness-test-secret"),
    )
    app = create_app(settings)

    monkeypatch.setattr(
        "app.api.health.check_db_connectivity",
        lambda: (False, "Database connection failed"),
    )

    client = TestClient(app)
    # Liveness check must remain 200 OK
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"
