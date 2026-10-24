"""Pytest configuration and common fixtures for HeatShield Bharat."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Provide isolated settings for test execution."""
    return Settings(
        APP_NAME="HeatShield Bharat API Test",
        APP_VERSION="0.1.0-test",
        APP_ENV="testing",
        DEBUG=True,
        API_PREFIX="/api/v1",
        LOG_LEVEL="WARNING",
        SECRET_KEY=SecretStr("test-secret-key-not-for-production-use"),
        CORS_ORIGINS=["http://localhost:5173", "http://testserver"],
        DATABASE_URL=None,
    )


@pytest.fixture
def app(test_settings: Settings):
    """Provide a fresh FastAPI app instance initialized with test settings."""
    return create_app(settings=test_settings)


@pytest.fixture
def client(app) -> TestClient:
    """Provide a TestClient for making requests to the test app."""
    return TestClient(app, raise_server_exceptions=False)
