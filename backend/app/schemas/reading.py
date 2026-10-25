"""Pydantic schemas for sensor reading telemetry ingestion and responses.

Conforms to docs/contracts/sensor-reading.schema.json and Module 2 API contracts.
"""

from datetime import datetime, timezone
import math
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.device import PaginationMeta


class ReadingCreateRequest(BaseModel):
    """Schema for POST /api/v1/readings ingestion payload."""

    model_config = ConfigDict(extra="forbid")

    device_code: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Stable non-secret device identifier. Must match a registered active device.",
        examples=["HS-WS01-D001"],
    )
    event_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Monotonically increasing per-device event identifier used for deduplication.",
        examples=["evt-00042"],
    )
    measured_at: datetime | None = Field(
        default=None,
        description="UTC timestamp from device clock at time of measurement. Nullable if clock is uncalibrated.",
        examples=["2026-11-15T10:30:00Z"],
    )
    temperature_c: float | None = Field(
        default=None,
        ge=-50.0,
        le=100.0,
        description="Ambient temperature in degrees Celsius (-50 to +100). Nullable for missing data.",
        examples=[38.5],
    )
    relative_humidity_pct: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Relative humidity in percent (0 to 100). Nullable for missing data.",
        examples=[72.3],
    )
    firmware_version: str | None = Field(
        default=None,
        max_length=50,
        description="Firmware version reported by the device.",
        examples=["0.1.0"],
    )
    source_mode: Literal["hardware", "simulated"] = Field(
        default="hardware",
        description="Distinguishes real physical measurements from simulated/test fixture data.",
    )

    @field_validator("temperature_c", "relative_humidity_pct")
    @classmethod
    def validate_finite_numbers(cls, value: float | None) -> float | None:
        """Reject non-finite floating point numbers (NaN, Infinity)."""
        if value is not None and (math.isnan(value) or math.isinf(value)):
            raise ValueError("Numeric reading values must be finite numbers (NaN and Infinity not allowed).")
        return value

    @field_validator("measured_at")
    @classmethod
    def normalize_utc_timestamp(cls, value: datetime | None) -> datetime | None:
        """Ensure measured_at is timezone-aware and represented in UTC."""
        if value is None:
            return None
        if value.tzinfo is None:
            # Assume UTC if naive
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ReadingData(BaseModel):
    """Full telemetry reading record representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    event_id: str
    measured_at: datetime | None
    received_at: datetime
    temperature_c: float | None
    relative_humidity_pct: float | None
    quality_status: str
    source_mode: str
    firmware_version: str | None
    created_at: datetime


class ReadingResponse(BaseModel):
    """Response returned when a new reading is ingested (HTTP 201 Created)."""

    data: ReadingData


class ReadingDeduplicatedResponse(BaseModel):
    """Response returned on idempotent retry of an existing event (HTTP 200 OK)."""

    data: ReadingData
    deduplicated: bool = True


class LatestReadingItem(BaseModel):
    """Latest reading record including device code."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    device_code: str
    event_id: str
    measured_at: datetime | None = None
    received_at: datetime
    temperature_c: float | None = None
    relative_humidity_pct: float | None = None
    quality_status: str
    source_mode: str
    firmware_version: str | None = None


class LatestReadingsResponse(BaseModel):
    """Response returned by GET /api/v1/readings/latest."""

    data: list[LatestReadingItem]


class ReadingHistoryItem(BaseModel):
    """Historical reading record conforming to API contracts Section 4.3."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    device_code: str
    event_id: str
    measured_at: datetime | None = None
    received_at: datetime
    temperature_c: float | None = None
    relative_humidity_pct: float | None = None
    quality_status: str
    source_mode: str
    firmware_version: str | None = None
    heat_index_c: float | None = None
    heat_index_screening_level: str | None = None
    heat_index_method: str | None = None


class ReadingSummaryMetric(BaseModel):
    """Descriptive statistics (min, max, mean) for a numeric metric."""

    min: float | None = None
    max: float | None = None
    mean: float | None = None


class ReadingHistorySummary(BaseModel):
    """Descriptive statistical summary of readings in the queried window."""

    start_time: datetime | None = None
    end_time: datetime | None = None
    total_readings: int = 0
    valid_readings: int = 0
    invalid_readings: int = 0
    suspect_readings: int = 0
    missing_readings: int = 0
    temperature_c: ReadingSummaryMetric
    relative_humidity_pct: ReadingSummaryMetric
    heat_index_c: ReadingSummaryMetric
    notes: str = (
        "Descriptive statistics computed from valid readings only. Invalid/suspect "
        "readings are excluded from temperature and humidity aggregates. Screening statistics only; "
        "does not infer worker exposure duration, medical risk, or certified safety outcomes."
    )


class ReadingHistoryQueryMeta(BaseModel):
    """Echo of query filters applied."""

    device_id: uuid.UUID | None = None
    worksite_id: uuid.UUID | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    quality_status: str | None = None


class ReadingHistoryResponse(BaseModel):
    """Response returned by GET /api/v1/readings/history adhering to API contracts."""

    data: list[ReadingHistoryItem]
    pagination: PaginationMeta
    query: ReadingHistoryQueryMeta
    summary: ReadingHistorySummary

