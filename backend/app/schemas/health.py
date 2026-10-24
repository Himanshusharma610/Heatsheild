"""Health and readiness check response schemas."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for liveness check (GET /health)."""

    status: Literal["healthy", "degraded"] = Field(
        default="healthy",
        description="Liveness status of the API service",
    )
    timestamp: datetime = Field(
        ...,
        description="Current server timestamp in UTC (ISO 8601)",
    )
    version: str = Field(
        ...,
        description="Application version",
    )


class ReadyResponse(BaseModel):
    """Response model for readiness check (GET /ready)."""

    status: Literal["ready", "not_ready"] = Field(
        default="ready",
        description="Readiness status of the application",
    )
    timestamp: datetime = Field(
        ...,
        description="Current server timestamp in UTC (ISO 8601)",
    )
    version: str = Field(
        ...,
        description="Application version",
    )
    services: dict[str, str] = Field(
        default_factory=dict,
        description="Status of individual system dependencies and components",
    )
