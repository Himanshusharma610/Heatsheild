"""Automated unit and integration tests for explainable Heat-Risk Calculation Engine (Module 7).

Verifies:
1. Reference examples from authoritative NOAA / NWS published tables
2. Celsius-to-Fahrenheit and inverse conversion correctness
3. Monotonic humidity and temperature behavior
4. Supported domain boundary limits (20°C to 55°C)
5. Out-of-domain handling (< 20°C, > 55°C, RH < 0%, RH > 100%)
6. Missing measurements handling (never substituting zero)
7. Non-finite values handling (NaN, Infinity)
8. Upstream quality-status propagation ('suspect', 'invalid', 'missing')
9. Determinism, method version, and equation-branch explainability
10. Prevention of false low-risk / normal results on invalid inputs
11. API endpoint integration: POST /api/v1/readings/calculate-heat-index
"""

import math
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas.heat_risk import (
    HeatIndexCalculationStatus,
    InformationalScreeningLevel,
)
from app.services.heat_index import (
    c_to_f,
    calculate_heat_index,
    f_to_c,
)


# ==============================================================================
# 1. Unit Conversion Correctness
# ==============================================================================

def test_unit_conversions():
    """Verify standard thermal conversion points."""
    assert c_to_f(0.0) == 32.0
    assert c_to_f(100.0) == 212.0
    assert c_to_f(-40.0) == -40.0
    assert round(c_to_f(37.0), 1) == 98.6

    assert f_to_c(32.0) == 0.0
    assert f_to_c(212.0) == 100.0
    assert f_to_c(-40.0) == -40.0
    assert round(f_to_c(98.6), 1) == 37.0


# ==============================================================================
# 2. Authoritative NOAA / NWS Reference Examples
# ==============================================================================

def test_noaa_reference_standard_case():
    """NOAA Table Lookup: 90°F (32.22°C) at 70% RH -> 106°F (41.1°C) rounded."""
    t_c = f_to_c(90.0)
    result = calculate_heat_index(temperature_c=t_c, relative_humidity_pct=70.0)

    assert result.status == HeatIndexCalculationStatus.VALID
    assert result.value_f == 105.9  # Exact 1-decimal NWS calculation
    assert round(result.value_f) == 106  # NOAA published integer table
    assert result.value_c == 41.1
    assert result.equation_applied == "rothfusz_standard"
    assert result.informational_screening_level == InformationalScreeningLevel.DANGER


def test_noaa_reference_high_humidity_adjustment():
    """NOAA Table Lookup: 86°F (30.0°C) at 90% RH triggers high-humidity adjustment -> 105°F (40.8°C) rounded."""
    t_c = f_to_c(86.0)
    result = calculate_heat_index(temperature_c=t_c, relative_humidity_pct=90.0)

    assert result.status == HeatIndexCalculationStatus.VALID
    assert result.value_f == 105.4  # Exact 1-decimal NWS calculation with adjustment
    assert round(result.value_f) == 105  # NOAA published integer table
    assert result.value_c == 40.8
    assert result.equation_applied == "rothfusz_high_humidity_adjusted"
    assert "high-humidity correction" in result.notes


def test_noaa_reference_low_humidity_adjustment():
    """NOAA Table Lookup: 100°F (37.78°C) at 10% RH triggers low-humidity adjustment -> 94°F (34.5°C) rounded."""
    t_c = f_to_c(100.0)
    result = calculate_heat_index(temperature_c=t_c, relative_humidity_pct=10.0)

    assert result.status == HeatIndexCalculationStatus.VALID
    assert result.value_f == 94.1  # Exact 1-decimal NWS calculation with adjustment
    assert round(result.value_f) == 94  # NOAA published integer table
    assert result.value_c == 34.5
    assert result.equation_applied == "rothfusz_low_humidity_adjusted"
    assert "low-humidity correction" in result.notes


def test_noaa_reference_steadman_simple_formula():
    """Steadman Simple Formula branch: 80°F (26.67°C) at 40% RH -> 80°F (26.4°C) rounded."""
    t_c = f_to_c(80.0)
    result = calculate_heat_index(temperature_c=t_c, relative_humidity_pct=40.0)

    assert result.status == HeatIndexCalculationStatus.VALID
    assert result.value_f == 79.6  # Exact 1-decimal Steadman simple formula
    assert round(result.value_f) == 80  # NOAA published integer table
    assert result.value_c == 26.4
    assert result.equation_applied == "steadman_simple"


# ==============================================================================
# 3. Monotonic Behavior
# ==============================================================================

def test_monotonic_humidity_increase():
    """At fixed temperature (35°C), increasing humidity strictly increases heat index."""
    t_c = 35.0
    hi_30 = calculate_heat_index(t_c, 30.0).value_c
    hi_50 = calculate_heat_index(t_c, 50.0).value_c
    hi_70 = calculate_heat_index(t_c, 70.0).value_c

    assert hi_30 is not None and hi_50 is not None and hi_70 is not None
    assert hi_30 < hi_50 < hi_70


def test_monotonic_temperature_increase():
    """At fixed humidity (50%), increasing temperature strictly increases heat index."""
    rh = 50.0
    hi_28 = calculate_heat_index(28.0, rh).value_c
    hi_35 = calculate_heat_index(35.0, rh).value_c
    hi_42 = calculate_heat_index(42.0, rh).value_c

    assert hi_28 is not None and hi_35 is not None and hi_42 is not None
    assert hi_28 < hi_35 < hi_42


# ==============================================================================
# 4. Domain Boundaries & Exclusions
# ==============================================================================

def test_domain_boundary_limits():
    """Boundary conditions 20.0°C and 55.0°C are valid; outside is out_of_domain."""
    # Min boundary (20.0 C) is valid
    res_min = calculate_heat_index(20.0, 50.0)
    assert res_min.status == HeatIndexCalculationStatus.VALID

    # Max boundary (55.0 C) is valid
    res_max = calculate_heat_index(55.0, 20.0)
    assert res_max.status == HeatIndexCalculationStatus.VALID

    # Below domain (< 20.0 C)
    res_cold = calculate_heat_index(18.0, 50.0)
    assert res_cold.status == HeatIndexCalculationStatus.OUT_OF_DOMAIN
    assert res_cold.value_c is None
    assert res_cold.informational_screening_level == InformationalScreeningLevel.UNAVAILABLE
    assert "below the 20.0°C operating domain" in res_cold.notes

    # Above domain (> 55.0 C)
    res_hot = calculate_heat_index(58.0, 20.0)
    assert res_hot.status == HeatIndexCalculationStatus.OUT_OF_DOMAIN
    assert res_hot.value_c is None
    assert res_hot.informational_screening_level == InformationalScreeningLevel.UNAVAILABLE
    assert "exceeds the 55.0°C empirical upper boundary" in res_hot.notes


def test_invalid_relative_humidity():
    """Humidity outside [0, 100] returns invalid_input."""
    res_neg = calculate_heat_index(30.0, -5.0)
    assert res_neg.status == HeatIndexCalculationStatus.INVALID_INPUT
    assert res_neg.value_c is None

    res_over = calculate_heat_index(30.0, 105.0)
    assert res_over.status == HeatIndexCalculationStatus.INVALID_INPUT
    assert res_over.value_c is None


# ==============================================================================
# 5. Missing & Non-Finite Inputs
# ==============================================================================

def test_missing_data_returns_unavailable():
    """Missing temperature or humidity returns missing_data and NEVER defaults to zero or normal."""
    res1 = calculate_heat_index(None, 50.0)
    assert res1.status == HeatIndexCalculationStatus.MISSING_DATA
    assert res1.value_c is None
    assert res1.informational_screening_level == InformationalScreeningLevel.UNAVAILABLE

    res2 = calculate_heat_index(30.0, None)
    assert res2.status == HeatIndexCalculationStatus.MISSING_DATA
    assert res2.value_c is None

    res3 = calculate_heat_index(None, None)
    assert res3.status == HeatIndexCalculationStatus.MISSING_DATA
    assert res3.value_c is None


def test_non_finite_inputs():
    """NaN and infinite inputs return invalid_input."""
    res_nan = calculate_heat_index(float("nan"), 50.0)
    assert res_nan.status == HeatIndexCalculationStatus.INVALID_INPUT
    assert res_nan.value_c is None

    res_inf = calculate_heat_index(30.0, float("inf"))
    assert res_inf.status == HeatIndexCalculationStatus.INVALID_INPUT
    assert res_inf.value_c is None


# ==============================================================================
# 6. Quality Status Propagation
# ==============================================================================

def test_quality_status_handling():
    """Upstream quality status is respected and surfaced in calculation outcome."""
    # Invalid upstream quality rejects calculation
    res_invalid = calculate_heat_index(32.0, 60.0, quality_status="invalid")
    assert res_invalid.status == HeatIndexCalculationStatus.INVALID_QUALITY
    assert res_invalid.value_c is None

    # Missing upstream quality rejects calculation
    res_missing = calculate_heat_index(32.0, 60.0, quality_status="missing")
    assert res_missing.status == HeatIndexCalculationStatus.MISSING_DATA
    assert res_missing.value_c is None

    # Suspect upstream quality calculates value but flags suspect_quality with audit warning
    res_suspect = calculate_heat_index(32.0, 60.0, quality_status="suspect")
    assert res_suspect.status == HeatIndexCalculationStatus.SUSPECT_QUALITY
    assert res_suspect.value_c is not None
    assert "suspect" in res_suspect.notes


# ==============================================================================
# 7. Traceability, Determinism & Limitations
# ==============================================================================

def test_traceability_and_limitations():
    """Every result includes method version, input provenance, and scientific disclaimers."""
    result = calculate_heat_index(36.0, 65.0)

    assert result.method == "NWS_ROTHFUSZ_1990"
    assert result.method_version == "1.0.0"
    assert result.input_temperature_c == 36.0
    assert result.input_relative_humidity_pct == 65.0
    assert len(result.limitations) >= 5
    assert any("NOT Wet Bulb Globe Temperature" in item for item in result.limitations)
    assert any("sunlight" in item for item in result.limitations)
    assert any("medical diagnosis" in item for item in result.limitations)


def test_calculation_determinism():
    """Repeated calls with identical inputs return identical results."""
    res1 = calculate_heat_index(37.5, 72.0)
    res2 = calculate_heat_index(37.5, 72.0)

    assert res1.value_c == res2.value_c
    assert res1.value_f == res2.value_f
    assert res1.equation_applied == res2.equation_applied
    assert res1.informational_screening_level == res2.informational_screening_level


# ==============================================================================
# 8. API Endpoint Integration Tests
# ==============================================================================

@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        APP_NAME="HeatShield Bharat Risk Engine Test",
        APP_ENV="testing",
        DEBUG=True,
        API_PREFIX="/api/v1",
        DATABASE_URL=None,
    )
    app = create_app(settings)
    return TestClient(app, raise_server_exceptions=False)


def test_api_calculate_heat_index_success(client: TestClient):
    """POST /api/v1/readings/calculate-heat-index returns 200 with full explainability."""
    payload = {
        "temperature_c": 35.0,
        "relative_humidity_pct": 60.0,
        "quality_status": "valid",
    }
    response = client.post("/api/v1/readings/calculate-heat-index", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "valid"
    assert data["indicator_name"] == "heat_index"
    assert data["value_c"] is not None
    assert data["value_f"] is not None
    assert data["unit"] == "celsius"
    assert data["method"] == "NWS_ROTHFUSZ_1990"
    assert data["method_version"] == "1.0.0"
    assert "limitations" in data
    assert len(data["limitations"]) > 0


def test_api_calculate_heat_index_out_of_domain(client: TestClient):
    """Sub-20°C temperatures return 200 with out_of_domain status and null value."""
    payload = {
        "temperature_c": 12.0,
        "relative_humidity_pct": 50.0,
    }
    response = client.post("/api/v1/readings/calculate-heat-index", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "out_of_domain"
    assert data["value_c"] is None
    assert data["informational_screening_level"] == "unavailable"


def test_api_calculate_heat_index_missing_fields(client: TestClient):
    """Missing input parameters returns 200 with missing_data status."""
    payload = {
        "temperature_c": None,
        "relative_humidity_pct": 50.0,
    }
    response = client.post("/api/v1/readings/calculate-heat-index", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "missing_data"
    assert data["value_c"] is None
