"""Application configuration management using Pydantic Settings.

Reads configuration from environment variables or a local `.env` file,
with validated defaults safe for local development. Secrets are protected
from accidental exposure.
"""

from functools import lru_cache
from typing import Literal
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema with environment-driven loading."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application metadata
    APP_NAME: str = Field(default="HeatShield Bharat API", description="Name of the application")
    APP_VERSION: str = Field(default="0.1.0", description="Semantic version of the application")
    APP_ENV: Literal["development", "staging", "production", "testing"] = Field(
        default="development",
        description="Deployment environment",
    )
    DEBUG: bool = Field(default=True, description="Enable debug mode and verbose errors in dev")

    # Server binding
    HOST: str = Field(default="0.0.0.0", description="Host interface to bind")
    PORT: int = Field(default=8000, description="Port to listen on")

    # API Routing
    API_PREFIX: str = Field(default="/api/v1", description="Prefix for versioned API routes")

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # Security
    SECRET_KEY: SecretStr = Field(
        default=SecretStr("dev-insecure-secret-key-change-in-production"),
        description="Secret key for cryptographic signing (must be overridden in production)",
    )

    # CORS origins
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"],
        description="Allowed origins for CORS requests",
    )

    # Database configuration (Module 4)
    DATABASE_URL: str | None = Field(
        default=None,
        description="PostgreSQL connection string (e.g. postgresql://user:pass@localhost:5432/dbname)",
    )
    DB_POOL_SIZE: int = Field(default=5, description="Maximum persistent connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Maximum overflow connections beyond pool size")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Connection acquisition timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=1800, description="Connection recycle interval in seconds")

    @property
    def safe_database_url(self) -> str | None:
        """Return DATABASE_URL with sensitive credentials masked for safe logging."""
        if not self.DATABASE_URL:
            return None
        from urllib.parse import urlsplit, urlunsplit
        try:
            parts = urlsplit(self.DATABASE_URL)
            if parts.password:
                user = parts.username or ""
                host = parts.hostname or ""
                port = f":{parts.port}" if parts.port else ""
                netloc = f"{user}:***@{host}{port}"
                return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
            return self.DATABASE_URL
        except Exception:
            return "postgresql://***"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: str | list[str]) -> list[str]:
        """Allow CORS origins to be specified as a comma-separated string or list."""
        if isinstance(value, str):
            # Split comma-separated string and strip whitespace
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("API_PREFIX")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        """Ensure API prefix starts with / and does not end with /."""
        cleaned = "/" + value.strip("/")
        return cleaned


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton.

    Can be overridden in tests using FastAPI dependency injection or lru_cache clearing.
    """
    return Settings()
