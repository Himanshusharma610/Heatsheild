"""Sensor reading telemetry API endpoints (Module 6).

Implements POST /api/v1/readings with device authentication, schema validation,
idempotent deduplication, and transactional persistence.
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.device_auth import authenticate_device, extract_device_token
from app.db.session import get_db
from app.schemas.common import ErrorResponse
from app.schemas.reading import (
    ReadingCreateRequest,
    ReadingData,
    ReadingDeduplicatedResponse,
    ReadingResponse,
)
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
