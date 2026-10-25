"""Tests for deployment configuration validation and security invariants (Module 14)."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_development_mode_allows_safe_defaults():
    """Development environment must permit local development defaults."""
    cfg = Settings(APP_ENV="development")
    assert cfg.APP_ENV == "development"
    assert cfg.DEBUG is True
    assert cfg.SECRET_KEY.get_secret_value() == "dev-insecure-secret-key-change-in-production"


def test_testing_mode_allows_empty_database_and_debug():
    """Testing environment must permit in-memory SQLite and isolated configs."""
    cfg = Settings(APP_ENV="testing", DATABASE_URL=None, DEBUG=True)
    assert cfg.APP_ENV == "testing"


def test_production_mode_rejects_debug_true():
    """Production mode must reject DEBUG=True to prevent stack trace disclosure."""
    with pytest.raises(ValidationError, match="DEBUG must be set to False"):
        Settings(
            APP_ENV="production",
            DEBUG=True,
            SECRET_KEY="a-secure-production-secret-key-at-least-32-chars-long",
            DATABASE_URL="postgresql://user:pass@db:5432/heatshield",
        )


def test_production_mode_rejects_default_secret_key():
    """Production mode must reject default dev secret key."""
    with pytest.raises(ValidationError, match="Default or insecure SECRET_KEY"):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            SECRET_KEY="dev-insecure-secret-key-change-in-production",
            DATABASE_URL="postgresql://user:pass@db:5432/heatshield",
        )


def test_production_mode_rejects_short_secret_key():
    """Production mode must reject secret keys with insufficient entropy (<32 characters)."""
    with pytest.raises(ValidationError, match="SECRET_KEY entropy insufficient"):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            SECRET_KEY="short-secret-key-too-few-chars",
            DATABASE_URL="postgresql://user:pass@db:5432/heatshield",
        )


def test_production_mode_requires_database_url():
    """Production mode must reject startup without a configured DATABASE_URL."""
    with pytest.raises(ValidationError, match="DATABASE_URL must be configured"):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            SECRET_KEY="a-secure-production-secret-key-at-least-32-chars-long",
            DATABASE_URL=None,
        )


def test_production_mode_rejects_sqlite_database():
    """Production mode must reject SQLite URLs in favor of PostgreSQL."""
    with pytest.raises(ValidationError, match="SQLite databases are not permitted in production"):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            SECRET_KEY="a-secure-production-secret-key-at-least-32-chars-long",
            DATABASE_URL="sqlite:///production.db",
        )


def test_production_mode_rejects_wildcard_cors():
    """Production mode must reject wildcard CORS origin '*' when credentials are enabled."""
    with pytest.raises(ValidationError, match="Wildcard '\\*' CORS_ORIGINS is forbidden"):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            SECRET_KEY="a-secure-production-secret-key-at-least-32-chars-long",
            DATABASE_URL="postgresql://user:pass@db:5432/heatshield",
            CORS_ORIGINS=["*"],
        )


def test_production_mode_valid_configuration_succeeds():
    """Production mode with compliant settings instantiates successfully."""
    cfg = Settings(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="a-secure-production-secret-key-at-least-32-chars-long",
        DATABASE_URL="postgresql://heatshield_prod:P@ssw0rdProd2026!@postgres:5432/heatshield_prod",
        CORS_ORIGINS=["https://heatshield.gov.in", "https://dashboard.heatshield.gov.in"],
    )
    assert cfg.APP_ENV == "production"
    assert cfg.DEBUG is False
    assert cfg.safe_database_url == "postgresql://heatshield_prod:***@postgres:5432/heatshield_prod"
