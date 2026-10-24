"""Tests for application factory, configuration, routing, and error handling."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, SecretStr

from app.config import Settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.main import create_app


def test_root_index_endpoint(client: TestClient) -> None:
    """Verify GET / returns service information and navigation links."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "HeatShield Bharat API Test"
    assert data["version"] == "0.1.0-test"
    assert data["environment"] == "testing"
    assert data["health_url"] == "/health"
    assert data["ready_url"] == "/ready"
    assert data["api_prefix"] == "/api/v1"
    assert data["docs_url"] == "/docs"


def test_api_v1_index_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1 returns API v1 metadata."""
    response = client.get("/api/v1")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "HeatShield Bharat API v1"
    assert data["status"] == "active"
    assert data["docs_url"] == "/docs"


def test_openapi_docs_accessible(client: TestClient) -> None:
    """Verify OpenAPI JSON and documentation are available in development/test."""
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    assert "swagger" in docs_resp.text.lower() or "html" in docs_resp.headers.get("content-type", "")

    schema_resp = client.get("/openapi.json")
    assert schema_resp.status_code == 200
    schema_data = schema_resp.json()
    assert "paths" in schema_data
    assert "/health" in schema_data["paths"]
    assert "/ready" in schema_data["paths"]
    assert "/api/v1" in schema_data["paths"]


def test_custom_api_prefix_configuration() -> None:
    """Verify API prefix is configurable via settings."""
    custom_settings = Settings(
        APP_NAME="Custom Prefix API",
        API_PREFIX="/api/v2",
        APP_ENV="testing",
        SECRET_KEY=SecretStr("custom-secret-key-12345"),
    )
    custom_app = create_app(custom_settings)
    custom_client = TestClient(custom_app)

    # v2 prefix should work
    v2_resp = custom_client.get("/api/v2/health")
    assert v2_resp.status_code == 200

    # Old v1 prefix should not be mounted
    v1_resp = custom_client.get("/api/v1/health")
    assert v1_resp.status_code == 404


def test_cors_headers(client: TestClient) -> None:
    """Verify CORS middleware responds with correct headers for allowed origins."""
    response = client.options(
        "/api/v1",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_404_not_found_standard_error_format(client: TestClient) -> None:
    """Verify 404 errors adhere to the Module 2 error contract."""
    response = client.get("/non-existent-endpoint")
    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]


def test_405_method_not_allowed_format(client: TestClient) -> None:
    """Verify 405 Method Not Allowed errors adhere to the Module 2 error contract."""
    response = client.post("/health")
    assert response.status_code == 405

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "message" in data["error"]


def test_request_validation_error_format() -> None:
    """Verify 422 RequestValidationError returns Module 2 standard envelope."""
    test_app = FastAPI()
    from app.core.exceptions import register_exception_handlers
    register_exception_handlers(test_app)

    class DummyPayload(BaseModel):
        reading_value: float = Field(..., ge=0.0, le=100.0)

    @test_app.post("/test-validation")
    async def dummy_endpoint(payload: DummyPayload):
        return {"received": payload.reading_value}

    test_client = TestClient(test_app)

    # Send value exceeding upper bound
    response = test_client.post("/test-validation", json={"reading_value": 150.0})
    assert response.status_code == 422

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "Request validation failed."
    assert "details" in data["error"]
    assert len(data["error"]["details"]) > 0

    first_detail = data["error"]["details"][0]
    assert first_detail["field"] == "reading_value"
    assert "less than or equal to 100" in first_detail["message"].lower() or "input" in first_detail or "value" in first_detail


def test_custom_app_exceptions() -> None:
    """Verify custom AppException subclasses map correctly to HTTP status codes and payloads."""
    test_app = FastAPI()
    from app.core.exceptions import register_exception_handlers
    register_exception_handlers(test_app)

    @test_app.get("/trigger-bad-request")
    async def trigger_bad_request():
        raise BadRequestException("Invalid sensor identifier format")

    @test_app.get("/trigger-unauthorized")
    async def trigger_unauthorized():
        raise UnauthorizedException("Missing bearer token")

    @test_app.get("/trigger-forbidden")
    async def trigger_forbidden():
        raise ForbiddenException("Device is deactivated")

    @test_app.get("/trigger-not-found")
    async def trigger_not_found():
        raise NotFoundException("Worksite not found")

    @test_app.get("/trigger-conflict")
    async def trigger_conflict():
        raise ConflictException("Device code already registered")

    test_client = TestClient(test_app)

    # 400
    r_bad = test_client.get("/trigger-bad-request")
    assert r_bad.status_code == 400
    assert r_bad.json()["error"]["code"] == "BAD_REQUEST"
    assert r_bad.json()["error"]["message"] == "Invalid sensor identifier format"

    # 401
    r_unauth = test_client.get("/trigger-unauthorized")
    assert r_unauth.status_code == 401
    assert r_unauth.json()["error"]["code"] == "UNAUTHORIZED"

    # 403
    r_forbid = test_client.get("/trigger-forbidden")
    assert r_forbid.status_code == 403
    assert r_forbid.json()["error"]["code"] == "FORBIDDEN"

    # 404
    r_nf = test_client.get("/trigger-not-found")
    assert r_nf.status_code == 404
    assert r_nf.json()["error"]["code"] == "NOT_FOUND"

    # 409
    r_conf = test_client.get("/trigger-conflict")
    assert r_conf.status_code == 409
    assert r_conf.json()["error"]["code"] == "CONFLICT"


def test_unhandled_exception_does_not_leak_details() -> None:
    """Verify 500 unhandled exceptions do not disclose internal stack traces or secrets."""
    test_app = FastAPI()
    from app.core.exceptions import register_exception_handlers
    register_exception_handlers(test_app)

    @test_app.get("/trigger-crash")
    async def trigger_crash():
        raise RuntimeError("Database connection string: postgresql://admin:super_secret_pw@db:5432/db")

    test_client = TestClient(test_app, raise_server_exceptions=False)
    response = test_client.get("/trigger-crash")
    assert response.status_code == 500

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert data["error"]["message"] == "An unexpected internal server error occurred."
    # Ensure sensitive string is never exposed to the client
    assert "super_secret_pw" not in response.text
    assert "Traceback" not in response.text


def test_settings_validation_and_parsing() -> None:
    """Verify configuration parsing, sanitization, and secret protection."""
    # Test comma-separated CORS string parsing
    settings = Settings(
        CORS_ORIGINS="http://localhost:5173, http://127.0.0.1:3000 , https://dashboard.heatshield.internal",
        API_PREFIX="api/v1/",
        SECRET_KEY=SecretStr("super-confidential-secret-value"),
    )
    assert settings.CORS_ORIGINS == [
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "https://dashboard.heatshield.internal",
    ]
    assert settings.API_PREFIX == "/api/v1"

    # SecretStr protects secret value in string formatting / repr
    assert "super-confidential-secret-value" not in str(settings.SECRET_KEY)
    assert "super-confidential-secret-value" not in repr(settings.SECRET_KEY)
    assert settings.SECRET_KEY.get_secret_value() == "super-confidential-secret-value"


def test_application_startup_without_database_or_hardware() -> None:
    """Verify application starts and functions without any external DB or hardware."""
    minimal_settings = Settings(
        DATABASE_URL=None,
        APP_ENV="development",
    )
    minimal_app = create_app(minimal_settings)
    client = TestClient(minimal_app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
