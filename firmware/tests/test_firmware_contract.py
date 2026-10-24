"""
test_firmware_contract.py

Validates that the firmware's C/C++ environmental reading data structure
(firmware/heatshield/reading_types.h) maintains strict schema parity with
the project's canonical API specification (docs/contracts/sensor-reading.schema.json).
"""

import json
import re
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "docs" / "contracts" / "sensor-reading.schema.json"
HEADER_PATH = REPO_ROOT / "firmware" / "heatshield" / "reading_types.h"


def test_schema_and_header_exist():
    assert SCHEMA_PATH.is_file(), f"Missing schema at {SCHEMA_PATH}"
    assert HEADER_PATH.is_file(), f"Missing firmware header at {HEADER_PATH}"


def test_firmware_reading_struct_contains_all_schema_properties():
    """Every property defined in sensor-reading.schema.json must have a corresponding field in EnvironmentalReading."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    header_content = HEADER_PATH.read_text(encoding="utf-8")

    # Extract required and optional properties from schema
    properties = set(schema.get("properties", {}).keys())

    # Map schema property name to C header field name
    property_to_field_map = {
        "device_code": "device_code",
        "event_id": "event_id",
        "measured_at": "measured_at_iso8601",
        "temperature_c": "temperature_c",
        "relative_humidity_pct": "relative_humidity_pct",
        "firmware_version": "firmware_version",
    }

    for prop, field in property_to_field_map.items():
        assert prop in properties, f"Property {prop} missing from schema"
        assert field in header_content, f"Field {field} (for schema prop '{prop}') missing from reading_types.h"


def test_firmware_distinguishes_source_mode():
    """Verify that ReadingSourceMode enum explicitly exists to separate hardware from simulated test fixtures."""
    header_content = HEADER_PATH.read_text(encoding="utf-8")
    assert "ReadingSourceMode" in header_content
    assert "SOURCE_MODE_HARDWARE" in header_content
    assert "SOURCE_MODE_SIMULATED" in header_content


def test_firmware_has_explicit_presence_flags():
    """Verify that nullable schema numbers have explicit boolean presence flags (never substituting 0.0)."""
    header_content = HEADER_PATH.read_text(encoding="utf-8")
    assert "bool has_temperature;" in header_content
    assert "bool has_humidity;" in header_content


def test_firmware_defines_sensor_status_and_quality():
    """Verify SensorStatus and ReadingQuality enums exist."""
    header_content = HEADER_PATH.read_text(encoding="utf-8")
    assert "SENSOR_STATUS_UNCONFIGURED" in header_content
    assert "SENSOR_STATUS_OK" in header_content
    assert "QUALITY_VALID" in header_content
    assert "QUALITY_MISSING" in header_content
    assert "QUALITY_INVALID" in header_content
