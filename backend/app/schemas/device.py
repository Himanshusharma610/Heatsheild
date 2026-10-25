"""Device API schemas conforming to docs/architecture/api-contracts.md Section 3."""

from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field


DeviceStatus = Literal["registered", "online", "offline", "deactivated"]


class DeviceData(BaseModel):
    """Device representation in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_code: str
    worksite_id: uuid.UUID
    display_name: str | None = None
    status: DeviceStatus
    firmware_version: str | None = None
    last_seen_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PaginationMeta(BaseModel):
    """Pagination metadata conforming to API contracts."""

    total: int
    limit: int
    offset: int
    has_more: bool


class DeviceListResponse(BaseModel):
    """Response returned by GET /api/v1/devices."""

    data: list[DeviceData]
    pagination: PaginationMeta
