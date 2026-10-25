"""Pydantic schemas for explainable heat-risk calculation (Module 7).

Provides transparent data structures capturing calculation status, numerical values,
units, formula version, input provenance, and scientific limitations.
"""

from datetime import datetime, timezone
from enum import Enum
import math
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HeatIndexCalculationStatus(str, Enum):
    """Execution outcome status for heat index evaluation."""

    VALID = "valid"
    SUSPECT_QUALITY = "suspect_quality"
    OUT_OF_DOMAIN = "out_of_domain"
    MISSING_DATA = "missing_data"
    INVALID_INPUT = "invalid_input"
    INVALID_QUALITY = "invalid_quality"
    STALE = "stale"


class InformationalScreeningLevel(str, Enum):
    """Provisional NOAA screening levels for informational decision-support only.

    DISCLAIMER: These reference levels are NOT an official, approved regulatory
    standard for Indian worksites.
    """

    NORMAL = "normal"
    CAUTION = "caution"
    EXTREME_CAUTION = "extreme_caution"
    DANGER = "danger"
    EXTREME_DANGER = "extreme_danger"
    UNAVAILABLE = "unavailable"


class HeatIndexCalculationRequest(BaseModel):
    """Request payload for on-demand heat index calculation."""

    model_config = ConfigDict(extra="forbid")

    temperature_c: float | None = Field(
        default=None,
        description="Dry-bulb ambient air temperature in degrees Celsius.",
        examples=[38.5],
    )
    relative_humidity_pct: float | None = Field(
        default=None,
        description="Relative humidity percentage (0 to 100).",
        examples=[65.0],
    )
    quality_status: Literal["valid", "suspect", "invalid", "missing", "stale"] | None = Field(
        default="valid",
        description="Upstream data quality classification from reading validation engine.",
    )
    is_stale: bool = Field(
        default=False,
        description="Indicates whether the reading timestamp exceeds the maximum freshness threshold.",
    )

    @field_validator("temperature_c", "relative_humidity_pct")
    @classmethod
    def validate_finite(cls, val: float | None) -> float | None:
        if val is not None and (math.isnan(val) or math.isinf(val)):
            raise ValueError("Numeric values must be finite numbers (NaN and Infinity not allowed).")
        return val


class HeatIndexResult(BaseModel):
    """Explainable result produced by the HeatShield Bharat Heat Index Engine."""

    model_config = ConfigDict(extra="forbid")

    status: HeatIndexCalculationStatus = Field(
        ...,
        description="Calculation outcome status.",
    )
    indicator_name: str = Field(
        default="heat_index",
        description="Standardized name of the calculated environmental indicator.",
    )
    value_c: float | None = Field(
        default=None,
        description="Calculated Heat Index in degrees Celsius (rounded to 1 decimal place).",
        examples=[46.2],
    )
    value_f: float | None = Field(
        default=None,
        description="Calculated Heat Index in degrees Fahrenheit (rounded to 1 decimal place).",
        examples=[115.2],
    )
    unit: str = Field(
        default="celsius",
        description="Primary unit of the calculated output value.",
    )
    method: str = Field(
        default="NWS_ROTHFUSZ_1990",
        description="Authoritative reference method used for the calculation.",
    )
    method_version: str = Field(
        default="1.0.0",
        description="Semantic version of the calculation algorithm.",
    )
    equation_applied: str = Field(
        ...,
        description="Specific equation or branch applied (e.g. simple, rothfusz_adjusted, none).",
    )
    input_temperature_c: float | None = Field(
        default=None,
        description="Input dry-bulb air temperature in degrees Celsius.",
    )
    input_temperature_unit: str = Field(
        default="celsius",
        description="Unit of input dry-bulb temperature.",
    )
    input_relative_humidity_pct: float | None = Field(
        default=None,
        description="Input relative humidity in percent.",
    )
    input_humidity_unit: str = Field(
        default="percent",
        description="Unit of input relative humidity.",
    )
    informational_screening_level: InformationalScreeningLevel = Field(
        default=InformationalScreeningLevel.UNAVAILABLE,
        description=(
            "Provisional NOAA reference screening level. DISCLAIMER: Informational only; "
            "not an approved Indian occupational safety standard."
        ),
    )
    custom_classification: str | None = Field(
        default=None,
        description="Classification outcome from an optional external policy extension point.",
    )
    limitations: list[str] = Field(
        ...,
        description="Explicit scientific and operational limitations of the calculated value.",
    )
    notes: str = Field(
        ...,
        description="Calculation commentary, branch rationale, or domain exclusion warning.",
    )
    calculated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the calculation was performed.",
    )
