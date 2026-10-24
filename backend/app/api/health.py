"""Health and readiness endpoints.

Provides liveness and readiness probes for process monitoring and orchestrators.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status
from app.config import Settings, get_settings
from app.db.session import check_db_connectivity
from app.schemas.health import HealthResponse, ReadyResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Reports whether the API process is alive and able to respond to requests.",
    tags=["Health"],
)
async def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Report process liveness."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.APP_VERSION,
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness probe",
    description=(
        "Reports whether the application is ready to serve its currently implemented functionality. "
        "Performs a live database connectivity check if DATABASE_URL is configured."
    ),
    tags=["Health"],
)
async def get_ready(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> ReadyResponse:
    """Report application readiness.

    In Module 4, performs an active, bounded ping to the database when configured.
    An outage is accurately reported as 'unavailable' with a 503 status code.
    If no database is configured, reports 'not_configured'.
    """
    services: dict[str, str] = {"api": "ready"}
    overall_status: str = "ready"

    if settings.DATABASE_URL:
        db_alive, _ = check_db_connectivity()
        if db_alive:
            services["database"] = "connected"
        else:
            services["database"] = "unavailable"
            overall_status = "not_ready"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        services["database"] = "not_configured"

    return ReadyResponse(
        status=overall_status,  # type: ignore[arg-type]
        timestamp=datetime.now(timezone.utc),
        version=settings.APP_VERSION,
        services=services,
    )
