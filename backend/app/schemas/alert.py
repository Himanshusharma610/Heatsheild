"""Pydantic schemas for alert rules, alerts, and lifecycle management (Module 8).

Conforms to docs/architecture/api-contracts.md and Section 7 Heat-Risk Data Contract.
"""

from datetime import datetime
from enum import Enum
import math
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AlertSeverity(str, Enum):
    """Allowed alert severity classifications."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, Enum):
    """Allowed alert processing lifecycle states."""

    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class RuleOperator(str, Enum):
    """Supported mathematical comparison operators for rule evaluation."""

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"


class RuleMetric(str, Enum):
    """Supported physical metrics and derived indicators for rule evaluation."""

    TEMPERATURE_C = "temperature_c"
    RELATIVE_HUMIDITY_PCT = "relative_humidity_pct"
    HEAT_INDEX_C = "heat_index_c"
    HEAT_INDEX = "heat_index"  # Alias for heat_index_c


class AlertRuleCreateRequest(BaseModel):
    """Payload to create or configure an alert rule."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable name of the alert rule.",
        examples=["Extreme Heat Warning"],
    )
    worksite_id: uuid.UUID | None = Field(
        default=None,
        description="Optional worksite scope. If null, rule is evaluated globally across all worksites.",
    )
    metric: RuleMetric = Field(
        ...,
        description="Physical metric or derived indicator evaluated by this rule.",
        examples=["heat_index_c"],
    )
    operator: RuleOperator = Field(
        ...,
        description="Comparison operator ('gt', 'gte', 'lt', 'lte', 'eq').",
        examples=["gte"],
    )
    threshold_value: float = Field(
        ...,
        description="Numerical threshold value to compare against.",
        examples=[41.0],
    )
    threshold_params: dict[str, Any] | None = Field(
        default=None,
        description="Optional auxiliary configuration parameters (e.g. hysteresis band, duration).",
    )
    severity: AlertSeverity = Field(
        ...,
        description="Severity classification assigned to triggered alerts ('info', 'warning', 'critical', 'emergency').",
        examples=["warning"],
    )
    is_enabled: bool = Field(
        default=True,
        description="Whether this rule is actively evaluated against incoming readings.",
    )

    @field_validator("threshold_value")
    @classmethod
    def validate_finite_threshold(cls, val: float) -> float:
        """Reject non-finite numbers for threshold values."""
        if math.isnan(val) or math.isinf(val):
            raise ValueError("threshold_value must be a finite number (NaN and Infinity not allowed).")
        return val


class AlertRuleData(BaseModel):
    """Representation of an alert rule entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    worksite_id: uuid.UUID | None
    metric: str
    operator: str
    threshold_value: float | None
    threshold_params: dict[str, Any] | None
    severity: str
    is_enabled: bool
    rule_version: int
    created_at: datetime
    updated_at: datetime


class AlertPagination(BaseModel):
    """Pagination metadata conforming to API contracts."""

    total: int
    limit: int
    offset: int
    has_more: bool


class AlertRuleListResponse(BaseModel):
    """Paginated list of configured alert rules."""

    data: list[AlertRuleData]
    pagination: AlertPagination


class AlertRuleResponse(BaseModel):
    """Single alert rule response."""

    data: AlertRuleData


class AlertData(BaseModel):
    """Representation of an alert event entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    device_code: str | None = None
    reading_id: uuid.UUID | None = None
    alert_rule_id: uuid.UUID | None = None
    alert_rule_name: str | None = None
    event_type: str
    severity: str
    status: str
    rule_version_snapshot: int | None = None
    deduplication_key: str | None = None
    triggered_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class AlertListResponse(BaseModel):
    """Paginated list of alerts conforming to API contracts."""

    data: list[AlertData]
    pagination: AlertPagination


class AlertAcknowledgeRequest(BaseModel):
    """Request payload for alert acknowledgement."""

    model_config = ConfigDict(extra="forbid")

    action_taken: str | None = Field(
        default=None,
        max_length=2000,
        description="Documented corrective or safety action taken in response to this alert.",
        examples=["Workers moved to shaded rest area. Cold drinking water distributed."],
    )


class AlertAcknowledgementData(BaseModel):
    """Audit record of an acknowledgement action."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    action_taken: str | None
    acknowledged_at: datetime


class AlertAcknowledgeResponseData(BaseModel):
    """Response payload for successful alert acknowledgement."""

    id: uuid.UUID
    status: str
    acknowledged_at: datetime
    acknowledgement: AlertAcknowledgementData


class AlertAcknowledgeResponse(BaseModel):
    """Envelope for alert acknowledgement response."""

    data: AlertAcknowledgeResponseData


class AlertResolveRequest(BaseModel):
    """Request payload for manual alert resolution."""

    model_config = ConfigDict(extra="forbid")

    resolution_notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Notes regarding resolution and safe conditions confirmation.",
        examples=["Ambient heat index dropped below threshold. Normal work resumed with monitoring."],
    )


class AlertResolveResponseData(BaseModel):
    """Response payload for successful alert resolution."""

    id: uuid.UUID
    status: str
    resolved_at: datetime


class AlertResolveResponse(BaseModel):
    """Envelope for alert resolution response."""

    data: AlertResolveResponseData
