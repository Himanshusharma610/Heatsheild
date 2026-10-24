"""Tests for health and readiness endpoints."""

from datetime import datetime, timezone
from fastapi.testclient import TestClient


def test_health_endpoint_success(client: TestClient) -> None:
    """Verify GET /health reports liveness with healthy status and metadata."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0-test"

    # Verify timestamp format is valid ISO 8601 UTC
    parsed_time = datetime.fromisoformat(data["timestamp"])
    assert parsed_time.tzinfo is not None or "Z" in data["timestamp"] or parsed_time.utcoffset() == timezone.utc.utcoffset(None)


def test_ready_endpoint_success(client: TestClient) -> None:
    """Verify GET /ready reports accurate application readiness without pretending DB is connected."""
    response = client.get("/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert data["version"] == "0.1.0-test"

    # Accurate readiness: api is ready, database is not configured
    services = data.get("services", {})
    assert services.get("api") == "ready"
    assert services.get("database") == "not_configured"

    # Verify timestamp format
    parsed_time = datetime.fromisoformat(data["timestamp"])
    assert parsed_time is not None


def test_health_under_versioned_prefix(client: TestClient) -> None:
    """Verify health and ready probes are also accessible under the /api/v1 prefix."""
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    ready_resp = client.get("/api/v1/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"
