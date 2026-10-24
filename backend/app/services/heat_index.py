"""Explainable environmental heat-risk calculation service (Module 7).

Implements the authoritative National Weather Service (NWS) / NOAA Heat Index
algorithm derived from physiological modeling by Robert G. Steadman (1979) and
multiple regression equations by Lans P. Rothfusz (1990).

CRITICAL SCIENTIFIC & SAFETY CONSTRAINTS:
1. Heat Index is NOT Wet Bulb Globe Temperature (WBGT).
   It does not measure radiant heat (solar radiation) or wind velocity.
2. The model assumes shade, light wind (5 knots / 2.5 m/s), and normal clothing.
   Direct sunlight can increase apparent heat stress by up to 8°C (15°F).
3. No clinical or diagnostic claims: Does NOT predict heatstroke or diagnose medical conditions.
4. No unapproved official standards: Informational screening levels are strictly provisional
   decision-support aids and do not constitute an official Indian occupational regulation.
"""

from datetime import datetime, timezone
import math

from app.schemas.heat_risk import (
    HeatIndexCalculationStatus,
    HeatIndexResult,
    InformationalScreeningLevel,
)

METHOD_NAME = "NWS_ROTHFUSZ_1990"
METHOD_VERSION = "1.0.0"

# Operating domain limits in Celsius (corresponds to ~68°F to 131°F)
DOMAIN_MIN_TEMP_C = 20.0
DOMAIN_MAX_TEMP_C = 55.0

# Rothfusz 9-term polynomial regression coefficients
C1 = -42.379
C2 = 2.04901523
C3 = 10.14333127
C4 = -0.22475541
C5 = -0.00683783
C6 = -0.05481717
C7 = 0.00122874
C8 = 0.00085282
C9 = -0.00000199

STANDARD_LIMITATIONS = [
    "Heat Index is an environmental screening indicator, NOT Wet Bulb Globe Temperature (WBGT).",
    "Assumes shade, light wind (approx. 5 knots / 2.5 m/s), standard atmospheric pressure, and typical light clothing.",
    "Exposure to direct, intense sunlight can increase apparent heat stress by up to 8°C (15°F).",
    "Does NOT account for personal metabolic workload, PPE encapsulation, hydration, age, acclimatization, or health conditions.",
    "Does NOT provide clinical medical diagnosis, heatstroke prediction, or official occupational compliance certification.",
]


def c_to_f(celsius: float) -> float:
    """Convert degrees Celsius to degrees Fahrenheit."""
    return (celsius * 9.0 / 5.0) + 32.0


def f_to_c(fahrenheit: float) -> float:
    """Convert degrees Fahrenheit to degrees Celsius."""
    return (fahrenheit - 32.0) * 5.0 / 9.0


def get_informational_screening_level(heat_index_c: float) -> InformationalScreeningLevel:
    """Map calculated Heat Index to provisional NOAA informational reference categories.

    DISCLAIMER: For informational decision-support only. Not an approved Indian
    occupational safety threshold.
    """
    if heat_index_c < 27.0:
        return InformationalScreeningLevel.NORMAL
    if heat_index_c < 32.2:  # < 90°F
        return InformationalScreeningLevel.CAUTION
    if heat_index_c < 39.4:  # < 103°F
        return InformationalScreeningLevel.EXTREME_CAUTION
    if heat_index_c < 51.7:  # < 125°F
        return InformationalScreeningLevel.DANGER
    return InformationalScreeningLevel.EXTREME_DANGER


def calculate_heat_index(
    temperature_c: float | None,
    relative_humidity_pct: float | None,
    quality_status: str | None = "valid",
) -> HeatIndexResult:
    """Calculate the NWS / Steadman / Rothfusz Heat Index deterministically.

    Args:
        temperature_c: Dry-bulb air temperature in degrees Celsius.
        relative_humidity_pct: Relative humidity in percent (0 to 100).
        quality_status: Upstream data quality flag ('valid', 'suspect', 'invalid', 'missing').

    Returns:
        Structured, explainable HeatIndexResult with numerical outputs, calculation
        provenance, equation branch, and explicit scientific limitations.
    """
    now = datetime.now(timezone.utc)

    # 1. Missing data checks
    if temperature_c is None or relative_humidity_pct is None:
        return HeatIndexResult(
            status=HeatIndexCalculationStatus.MISSING_DATA,
            equation_applied="none",
            input_temperature_c=temperature_c,
            input_relative_humidity_pct=relative_humidity_pct,
            informational_screening_level=InformationalScreeningLevel.UNAVAILABLE,
            limitations=STANDARD_LIMITATIONS,
            notes="Calculation unavailable: One or both required measurements (temperature, relative humidity) are missing.",
            calculated_at=now,
        )

    # 2. Upstream quality checks
    if quality_status == "invalid":
        return HeatIndexResult(
            status=HeatIndexCalculationStatus.INVALID_QUALITY,
            equation_applied="none",
            input_temperature_c=temperature_c,
            input_relative_humidity_pct=relative_humidity_pct,
            informational_screening_level=InformationalScreeningLevel.UNAVAILABLE,
            limitations=STANDARD_LIMITATIONS,
            notes="Calculation rejected: Upstream reading was flagged with 'invalid' quality status.",
            calculated_at=now,
        )

    if quality_status == "missing":
        return HeatIndexResult(
            status=HeatIndexCalculationStatus.MISSING_DATA,
            equation_applied="none",
            input_temperature_c=temperature_c,
            input_relative_humidity_pct=relative_humidity_pct,
            informational_screening_level=InformationalScreeningLevel.UNAVAILABLE,
            limitations=STANDARD_LIMITATIONS,
            notes="Calculation rejected: Upstream reading was flagged with 'missing' quality status.",
            calculated_at=now,
        )

    # 3. Numerical sanity checks
    if math.isnan(temperature_c) or math.isinf(temperature_c) or math.isnan(relative_humidity_pct) or math.isinf(relative_humidity_pct):
        return HeatIndexResult(
            status=HeatIndexCalculationStatus.INVALID_INPUT,
            equation_applied="none",
            input_temperature_c=temperature_c,
            input_relative_humidity_pct=relative_humidity_pct,
            informational_screening_level=InformationalScreeningLevel.UNAVAILABLE,
            limitations=STANDARD_LIMITATIONS,
            notes="Calculation failed: Non-finite numerical value detected (NaN or Infinity).",
            calculated_at=now,
        )

    # 4. Relative humidity physical boundaries
    if relative_humidity_pct < 0.0 or relative_humidity_pct > 100.0:
        return HeatIndexResult(
            status=HeatIndexCalculationStatus.INVALID_INPUT,
            equation_applied="none",
            input_temperature_c=temperature_c,
            input_relative_humidity_pct=relative_humidity_pct,
            informational_screening_level=InformationalScreeningLevel.UNAVAILABLE,
            limitations=STANDARD_LIMITATIONS,
            notes=f"Calculation failed: Relative humidity {relative_humidity_pct}% is outside physically possible atmospheric bounds [0, 100].",
            calculated_at=now,
        )

    # 5. Method operating domain verification
    if temperature_c < DOMAIN_MIN_TEMP_C:
        return HeatIndexResult(
            status=HeatIndexCalculationStatus.OUT_OF_DOMAIN,
            equation_applied="none",
            input_temperature_c=temperature_c,
            input_relative_humidity_pct=relative_humidity_pct,
            informational_screening_level=InformationalScreeningLevel.UNAVAILABLE,
            limitations=STANDARD_LIMITATIONS,
            notes=(
                f"Air temperature ({temperature_c:.1f}°C / {c_to_f(temperature_c):.1f}°F) is below the {DOMAIN_MIN_TEMP_C}°C "
                "operating domain for heat-stress evaluation. Heat Index is defined only for warm/sultry conditions."
            ),
            calculated_at=now,
        )

    if temperature_c > DOMAIN_MAX_TEMP_C:
        return HeatIndexResult(
            status=HeatIndexCalculationStatus.OUT_OF_DOMAIN,
            equation_applied="none",
            input_temperature_c=temperature_c,
            input_relative_humidity_pct=relative_humidity_pct,
            informational_screening_level=InformationalScreeningLevel.UNAVAILABLE,
            limitations=STANDARD_LIMITATIONS,
            notes=(
                f"Air temperature ({temperature_c:.1f}°C / {c_to_f(temperature_c):.1f}°F) exceeds the {DOMAIN_MAX_TEMP_C}°C "
                "empirical upper boundary of the Rothfusz regression equation. Mathematical extrapolation is unverified."
            ),
            calculated_at=now,
        )

    # 6. Mathematical Evaluation (NWS Algorithm)
    t_f = c_to_f(temperature_c)
    rh = relative_humidity_pct

    # Step A: Steadman's simple formula
    hi_simple_f = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))
    hi_avg_f = (hi_simple_f + t_f) / 2.0

    if hi_avg_f < 80.0:
        hi_f = hi_simple_f
        equation_branch = "steadman_simple"
        branch_notes = "Evaluated via Steadman's simple equation (average apparent temperature < 80°F)."
    else:
        # Step B: Full Rothfusz 9-term polynomial equation
        hi_full_f = (
            C1
            + (C2 * t_f)
            + (C3 * rh)
            + (C4 * t_f * rh)
            + (C5 * (t_f ** 2))
            + (C6 * (rh ** 2))
            + (C7 * (t_f ** 2) * rh)
            + (C8 * t_f * (rh ** 2))
            + (C9 * (t_f ** 2) * (rh ** 2))
        )

        # Step C: Low and High Humidity Adjustments
        if rh < 13.0 and 80.0 <= t_f <= 112.0:
            adjustment = ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t_f - 95.0)) / 17.0)
            hi_f = hi_full_f - adjustment
            equation_branch = "rothfusz_low_humidity_adjusted"
            branch_notes = "Evaluated via full Rothfusz polynomial with low-humidity correction (RH < 13%, T in 80-112°F)."
        elif rh > 85.0 and 80.0 <= t_f <= 87.0:
            adjustment = ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)
            hi_f = hi_full_f + adjustment
            equation_branch = "rothfusz_high_humidity_adjusted"
            branch_notes = "Evaluated via full Rothfusz polynomial with high-humidity correction (RH > 85%, T in 80-87°F)."
        else:
            hi_f = hi_full_f
            equation_branch = "rothfusz_standard"
            branch_notes = "Evaluated via standard full Rothfusz 9-term polynomial."

    hi_c = f_to_c(hi_f)

    # 7. Quality status reconciliation and screening level
    status = HeatIndexCalculationStatus.VALID
    if quality_status == "suspect":
        status = HeatIndexCalculationStatus.SUSPECT_QUALITY
        branch_notes += " NOTE: Input measurements carry an upstream 'suspect' quality classification."

    screening_level = get_informational_screening_level(hi_c)

    return HeatIndexResult(
        status=status,
        indicator_name="heat_index",
        value_c=round(hi_c, 1),
        value_f=round(hi_f, 1),
        unit="celsius",
        method=METHOD_NAME,
        method_version=METHOD_VERSION,
        equation_applied=equation_branch,
        input_temperature_c=temperature_c,
        input_relative_humidity_pct=relative_humidity_pct,
        informational_screening_level=screening_level,
        limitations=STANDARD_LIMITATIONS,
        notes=branch_notes,
        calculated_at=now,
    )
