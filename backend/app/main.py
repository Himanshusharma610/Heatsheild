"""FastAPI application entry point for HeatShield Bharat.

Provides application factory create_app(), configured routers,
CORS middleware, and centralized error handling.
"""

import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers


def setup_logging(log_level: str) -> None:
    """Configure standard logging format and level."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory for HeatShield Bharat FastAPI application.

    Args:
        settings: Optional Settings instance. If not provided, loaded from environment.

    Returns:
        Configured FastAPI application instance.
    """
    if settings is None:
        settings = get_settings()

    setup_logging(settings.LOG_LEVEL)

    # In development, expose OpenAPI docs; in production, keep configurable
    docs_enabled = settings.DEBUG or settings.APP_ENV != "production"

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "HeatShield Bharat — IoT-based Environmental Heat-Monitoring and Early-Warning System API."
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    # Store settings in application state and dependency override for request handlers
    app.state.settings = settings
    app.dependency_overrides[get_settings] = lambda: settings

    # Configure CORS middleware
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register centralized exception handlers
    register_exception_handlers(app)

    # Register root-level health probes (standard for load balancers / container probes)
    app.include_router(health_router, tags=["Health"])

    # Register versioned API router under configured prefix (default: /api/v1)
    app.include_router(api_v1_router, prefix=settings.API_PREFIX)

    # Root landing endpoint
    @app.get(
        "/",
        summary="Service index",
        description="Returns basic service metadata and documentation links.",
        tags=["General"],
    )
    async def root_index() -> dict[str, str | None]:
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "health_url": "/health",
            "ready_url": "/ready",
            "api_prefix": settings.API_PREFIX,
            "docs_url": "/docs" if docs_enabled else None,
        }

    return app


# Default application instance for Uvicorn ASGI server
app = create_app()


if __name__ == "__main__":
    import uvicorn

    current_settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=current_settings.HOST,
        port=current_settings.PORT,
        reload=current_settings.DEBUG,
    )
