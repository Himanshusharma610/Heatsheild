"""Device management API endpoints.

Conforms to docs/architecture/api-contracts.md Section 3.
"""

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.user_auth import require_authenticated_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.device import count_devices, list_devices
from app.schemas.common import ErrorResponse
from app.schemas.device import DeviceData, DeviceListResponse, PaginationMeta

router = APIRouter()


@router.get(
    "",
    response_model=DeviceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List registered devices",
    description="List registered physical sensor nodes, with optional filtering by worksite, status, or active flag.",
    responses={
        status.HTTP_200_OK: {
            "model": DeviceListResponse,
            "description": "Paginated list of devices.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication required.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error.",
        },
    },
)
def get_devices(
    worksite_id: uuid.UUID | None = Query(None, description="Filter by worksite UUID"),
    status_filter: str | None = Query(None, alias="status", description="Filter by device status"),
    is_active: bool | None = Query(True, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    _user: User = Depends(require_authenticated_user),
    session: Session = Depends(get_db),
) -> DeviceListResponse:
    """Retrieve registered devices with pagination."""
    devices = list_devices(
        session=session,
        worksite_id=worksite_id,
        status=status_filter,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    total = count_devices(
        session=session,
        worksite_id=worksite_id,
        status=status_filter,
        is_active=is_active,
    )

    items = [DeviceData.model_validate(d) for d in devices]
    has_more = (offset + limit) < total

    return DeviceListResponse(
        data=items,
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        ),
    )
