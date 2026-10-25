"""API version 1 router aggregation.

Registers versioned endpoints and serves as the mounting point for
future domain routers (devices, readings, alerts).
"""

from fastapi import APIRouter
from app.api.health import router as health_router

router = APIRouter()

# Mount health routes under /api/v1 as well for API consumers
router.include_router(health_router, tags=["Health"])


@router.get(
    "",
    summary="API v1 root info",
    description="Returns metadata about the API v1 surface.",
    tags=["General"],
)
@router.get(
    "/",
    include_in_schema=False,
)
async def api_v1_index() -> dict[str, str]:
    """Information endpoint for API v1."""
    return {
        "name": "HeatShield Bharat API v1",
        "status": "active",
        "docs_url": "/docs",
    }


from app.api.v1.alerts import router as alerts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.devices import router as devices_router
from app.api.v1.readings import router as readings_router
from app.api.v1.users import router as users_router

# Mount authentication router (Module 12)
router.include_router(auth_router, prefix="/auth", tags=["Auth"])

# Mount user management router (Module 12)
router.include_router(users_router, prefix="/users", tags=["Users"])

# Mount readings router (Module 6)
router.include_router(readings_router, prefix="/readings", tags=["Readings"])

# Mount alerts router (Module 8)
router.include_router(alerts_router, tags=["Alerts"])

# Mount devices router
router.include_router(devices_router, prefix="/devices", tags=["Devices"])

