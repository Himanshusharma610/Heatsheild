"""Sensor reading telemetry API endpoints (Module 6).

Implements POST /api/v1/readings with device authentication, schema validation,
idempotent deduplication, and transactional persistence.
"""

from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.device_auth import authenticate_device, extract_device_token
from app.core.exceptions import ValidationException
from app.core.user_auth import require_authenticated_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.schemas.device import PaginationMeta
from app.schemas.reading import (
    LatestReadingItem,
    LatestReadingsResponse,
    ReadingCreateRequest,
    ReadingData,
    ReadingDeduplicatedResponse,
    ReadingHistoryItem,
    ReadingHistoryQueryMeta,
    ReadingHistoryResponse,
    ReadingHistorySummary,
    ReadingResponse,
)
from app.schemas.heat_risk import HeatIndexCalculationRequest, HeatIndexResult
from app.services.heat_index import calculate_heat_index
from app.services.telemetry import ingest_telemetry_reading

router = APIRouter()


@router.post(
    "",
    response_model=ReadingResponse | ReadingDeduplicatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest sensor reading",
    description=(
        "Ingests an environmental reading from an authenticated ESP32 device node. "
        "Supports idempotent retries: identical retransmissions return HTTP 200 OK with "
        "'deduplicated: true'. Conflicting payloads with an existing event ID return HTTP 409 Conflict."
    ),
    responses={
        status.HTTP_201_CREATED: {
            "model": ReadingResponse,
            "description": "New environmental reading ingested successfully.",
        },
        status.HTTP_200_OK: {
            "model": ReadingDeduplicatedResponse,
            "description": "Idempotent retry: reading was previously recorded with identical measurements.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing, inactive, or invalid device authentication token.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Event ID collision with conflicting measurement values.",
        },
        getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422): {
            "model": ErrorResponse,
            "description": "Request body validation failure or unregistered device.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Database persistence failure.",
        },
    },
)
def ingest_reading(
    payload: ReadingCreateRequest,
    response: Response,
    raw_token: str = Depends(extract_device_token),
    session: Session = Depends(get_db),
) -> ReadingResponse | ReadingDeduplicatedResponse:
    """Ingest, validate, and persist an environmental telemetry reading."""
    device = authenticate_device(session=session, device_code=payload.device_code, raw_token=raw_token)
    reading, deduplicated = ingest_telemetry_reading(session=session, device=device, payload=payload)

    reading_data = ReadingData.model_validate(reading)

    if deduplicated:
        response.status_code = status.HTTP_200_OK
        return ReadingDeduplicatedResponse(data=reading_data, deduplicated=True)

    return ReadingResponse(data=reading_data)


@router.post(
    "/calculate-heat-index",
    response_model=HeatIndexResult,
    status_code=status.HTTP_200_OK,
    summary="Calculate explainable Heat Index",
    description=(
        "Evaluates the National Weather Service (NWS) Heat Index deterministically for given "
        "dry-bulb temperature and relative humidity inputs. Returns full explainability metadata, "
        "including equation branch, calculation status, method version, and scientific limitations. "
        "Does NOT persist data or claim medical diagnosis."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": HeatIndexResult,
            "description": "Calculated heat index result with explainability notes.",
        },
        getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422): {
            "model": ErrorResponse,
            "description": "Malformed input or non-finite numbers.",
        },
    },
)
def compute_heat_index_endpoint(
    payload: HeatIndexCalculationRequest,
) -> HeatIndexResult:
    """Evaluate NWS Heat Index deterministically with explainability metadata."""
    return calculate_heat_index(
        temperature_c=payload.temperature_c,
        relative_humidity_pct=payload.relative_humidity_pct,
        quality_status=payload.quality_status,
        is_stale=payload.is_stale,
    )


@router.get(
    "/latest",
    response_model=LatestReadingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest environmental readings",
    description="Retrieve the most recent reading for each device or for a specific device.",
    responses={
        status.HTTP_200_OK: {
            "model": LatestReadingsResponse,
            "description": "List of latest sensor readings per device.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication required.",
        },
    },
)
def get_latest_readings_endpoint(
    device_id: uuid.UUID | None = Query(None, description="Filter to a specific device UUID"),
    worksite_id: uuid.UUID | None = Query(None, description="Filter to a specific worksite UUID"),
    quality_status: str | None = Query(None, description="Filter by quality status"),
    _user: User = Depends(require_authenticated_user),
    session: Session = Depends(get_db),
) -> LatestReadingsResponse:
    """Retrieve the most recent reading for each device."""
    from app.repositories.reading import get_latest_readings

    rows = get_latest_readings(
        session=session,
        device_id=device_id,
        worksite_id=worksite_id,
        quality_status=quality_status,
    )
    items = []
    for reading, device_code in rows:
        items.append(
            LatestReadingItem(
                id=reading.id,
                device_id=reading.device_id,
                device_code=device_code,
                event_id=reading.event_id,
                measured_at=reading.measured_at,
                received_at=reading.received_at,
                temperature_c=float(reading.temperature_c) if reading.temperature_c is not None else None,
                relative_humidity_pct=float(reading.relative_humidity_pct) if reading.relative_humidity_pct is not None else None,
                quality_status=reading.quality_status,
                source_mode=reading.source_mode,
                firmware_version=reading.firmware_version,
            )
        )
    return LatestReadingsResponse(data=items)


def _normalize_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get(
    "/history",
    response_model=ReadingHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query historical readings and analytics",
    description=(
        "Query historical readings and descriptive statistics for a device or worksite within a time range. "
        "Enforces deterministic ordering, bounded date ranges (max 30 days), and parameter validation."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": ReadingHistoryResponse,
            "description": "Paginated historical readings and descriptive summary analytics.",
        },
        getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422): {
            "model": ErrorResponse,
            "description": "Validation error: invalid date ordering, exceeded window, or negative limits.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication required.",
        },
    },
)
def get_reading_history_endpoint(
    device_id: uuid.UUID | None = Query(None, description="Target device UUID"),
    worksite_id: uuid.UUID | None = Query(None, description="Target worksite UUID"),
    start_time: datetime | None = Query(None, description="Start of time range (inclusive)"),
    end_time: datetime | None = Query(None, description="End of time range (inclusive)"),
    quality_status: str | None = Query(None, description="Filter by quality status ('valid', 'suspect', etc.)"),
    order_asc: bool = Query(True, description="Order chronologically ascending (default True for time-series charts)"),
    limit: int = Query(50, ge=1, le=500, description="Page limit (max 500)"),
    offset: int = Query(0, ge=0, description="Page offset"),
    _user: User = Depends(require_authenticated_user),
    session: Session = Depends(get_db),
) -> ReadingHistoryResponse:
    """Retrieve historical telemetry with descriptive statistics."""
    from app.repositories.reading import count_reading_history, get_reading_history, get_reading_summary

    now_utc = datetime.now(timezone.utc)
    norm_end = _normalize_utc(end_time) if end_time is not None else now_utc
    norm_start = _normalize_utc(start_time) if start_time is not None else (norm_end - timedelta(hours=24))

    if norm_start > norm_end:
        raise ValidationException(
            message="start_time must be less than or equal to end_time.",
            details=[{"field": "start_time", "message": "start_time is after end_time."}],
        )

    if (norm_end - norm_start) > timedelta(days=30):
        raise ValidationException(
            message="Requested time range cannot exceed 30 days.",
            details=[{"field": "time_range", "message": "Time range exceeds the 30-day maximum limit."}],
        )

    total = count_reading_history(
        session=session,
        device_id=device_id,
        worksite_id=worksite_id,
        start_time=norm_start,
        end_time=norm_end,
        quality_status=quality_status,
    )

    rows = get_reading_history(
        session=session,
        device_id=device_id,
        worksite_id=worksite_id,
        start_time=norm_start,
        end_time=norm_end,
        quality_status=quality_status,
        order_asc=order_asc,
        limit=limit,
        offset=offset,
    )

    items: list[ReadingHistoryItem] = []
    for reading, device_code in rows:
        temp_val = float(reading.temperature_c) if reading.temperature_c is not None else None
        hum_val = float(reading.relative_humidity_pct) if reading.relative_humidity_pct is not None else None

        hi_val: float | None = None
        hi_level: str | None = None
        hi_method: str | None = None

        if reading.quality_status == "valid" and temp_val is not None and hum_val is not None:
            hi_res = calculate_heat_index(temp_val, hum_val, quality_status="valid")
            if hi_res.status == "valid" and hi_res.value_c is not None:
                hi_val = hi_res.value_c
                hi_level = hi_res.informational_screening_level
                hi_method = f"{hi_res.method}:{hi_res.method_version}"

        items.append(
            ReadingHistoryItem(
                id=reading.id,
                device_id=reading.device_id,
                device_code=device_code,
                event_id=reading.event_id,
                measured_at=reading.measured_at,
                received_at=reading.received_at,
                temperature_c=temp_val,
                relative_humidity_pct=hum_val,
                quality_status=reading.quality_status,
                source_mode=reading.source_mode,
                firmware_version=reading.firmware_version,
                heat_index_c=hi_val,
                heat_index_screening_level=hi_level,
                heat_index_method=hi_method,
            )
        )

    summary_dict = get_reading_summary(
        session=session,
        device_id=device_id,
        worksite_id=worksite_id,
        start_time=norm_start,
        end_time=norm_end,
        quality_status=quality_status,
    )

    pagination = PaginationMeta(
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )

    query_meta = ReadingHistoryQueryMeta(
        device_id=device_id,
        worksite_id=worksite_id,
        start_time=norm_start,
        end_time=norm_end,
        quality_status=quality_status,
    )

    return ReadingHistoryResponse(
        data=items,
        pagination=pagination,
        query=query_meta,
        summary=ReadingHistorySummary(**summary_dict),
    )
