# HeatShield Bharat — ESP32 Firmware

## 1. Overview & Current Status

This directory contains the firmware for the **HeatShield Bharat** environmental heat-monitoring device.

- **Current Implementation Phase:** **Module 5: Scaffolding and Sensor Abstraction**
- **Hardware Status:** `UNCONFIRMED`
  - No physical ESP32 board or sensor modules have been procured or wired yet.
  - All hardware-specific parameters (GPIO pins, I2C addresses, bus timings, sensor libraries) are marked `UNCONFIRMED`.
  - The firmware is built with an isolated **Hardware Abstraction Layer (HAL)** that runs safely on host machines and on unconfigured hardware without fabricating readings.
- **Fail-Safe Guarantee:** Missing, corrupted, or unconfigured sensor states evaluate strictly to `ALERT_LEVEL_UNKNOWN` and will never trigger a false "safe" (green) indicator.

For the comprehensive hardware evaluation and physical integration checklist, refer to:
👉 [Hardware Selection and Integration Guide](../docs/hardware/hardware-selection.md)

---

## 2. Firmware Directory Structure

```
firmware/
├── README.md                      # This document
├── heatshield/                    # Arduino sketch directory (matches .ino name)
│   ├── heatshield.ino             # Main Arduino sketch entry point (setup / loop)
│   ├── reading_types.h            # Typed environmental reading contract (matches API schema)
│   ├── sensor_interface.h         # Abstract sensor HAL (ISensor, UnconfiguredSensor, DiagnosticSimulatedSensor)
│   ├── validation.h               # Numerical sanity (NaN/Inf) and physical plausibility bounds engine
│   ├── alert_logic.h              # Autonomous, offline local alert evaluation & hysteresis
│   └── telemetry_boundary.h       # Decoupled telemetry publisher interface (zero hardcoded secrets)
└── tests/                         # Host-runnable test suites
    ├── test_firmware.cpp          # C++ unit tests (validation, alert logic, mock sensors, hysteresis)
    ├── test_firmware_contract.py  # Python parity test against docs/contracts/sensor-reading.schema.json
    └── run_tests.sh               # Test runner (native g++ or rootless Podman/Docker container)
```

---

## 3. Core Architecture & Modules

### 3.1 Reading Data Contract (`reading_types.h`)
- Implements `EnvironmentalReading` conforming strictly to `docs/contracts/sensor-reading.schema.json`.
- Features explicit presence flags (`has_temperature`, `has_humidity`) to ensure missing readings are **never** silently substituted with `0.0`.
- Includes an explicit `ReadingSourceMode` enum (`SOURCE_MODE_HARDWARE` vs `SOURCE_MODE_SIMULATED`) ensuring test fixtures can never masquerade as physical measurements.
- Tracks `SensorStatus` (`UNCONFIGURED`, `INITIALIZING`, `OK`, `ERROR`, `DISCONNECTED`) and `ReadingQuality` (`VALID`, `SUSPECT`, `INVALID`, `MISSING`).

### 3.2 Sensor Abstraction Layer (`sensor_interface.h`)
- Isolates physical bus protocols (I2C, OneWire, SPI) behind the `ISensor` base class.
- Includes `UnconfiguredSensor`: Safe default adapter that returns `false` on `begin()` and reports `SENSOR_STATUS_UNCONFIGURED`.
- Includes `DiagnosticSimulatedSensor`: Explicitly sets `SOURCE_MODE_SIMULATED` for diagnostic host tests.

### 3.3 Reading Validation Engine (`validation.h`)
- Hardware-independent plausibility validation.
- Validates against `PlausibilityBounds` (defaults: -20.0 °C to +70.0 °C, 0% to 100% RH).
- Detects non-finite floating-point states (`isnan()`, `isinf()`).
- Flags missing metrics and sensor hardware faults without silently clamping corrupted values.
- *Note:* Physical plausibility verification confirms data sanity; it does NOT assert sensor calibration accuracy.

### 3.4 Local Alert Evaluation (`alert_logic.h`)
- Evaluates environmental telemetry **completely offline**, ensuring worker protection without cellular, Wi-Fi, or cloud dependency.
- **Fail-safe Rule:** Any corrupted, missing, or unconfigured data evaluates to `ALERT_LEVEL_UNKNOWN`. It **never** evaluates to `ALERT_LEVEL_SAFE`.
- Employs stateful hysteresis (deadband) to prevent rapid threshold fluttering on temperature boundaries.
- Decouples alert actuators (piezo buzzers, RGB LEDs) behind `IAlertOutput` and `NullAlertOutput` to prevent blind writes to unconfirmed GPIO pins.
- *Disclaimer:* Scaffolding thresholds (35.0 °C caution, 40.0 °C danger) are provisional engineering placeholders and do not claim clinical heatstroke diagnosis or validated medical advisory status.

### 3.5 Telemetry Boundary (`telemetry_boundary.h`)
- Abstract interface `ITelemetryPublisher` isolates future Wi-Fi / MQTT / HTTP transmission.
- `UnconfiguredTelemetryPublisher` safely drops outgoing packets without blocking the local alert loop.
- Contains zero embedded credentials, Wi-Fi SSIDs, or API tokens.

---

## 4. Running Unit Tests

### 4.1 Host C++ Unit Tests
Host tests verify reading types, validation algorithms, alert thresholds, and hysteresis.

Using the automated runner:
```bash
./firmware/tests/run_tests.sh
```

Or manually using Podman/Docker:
```bash
podman run --rm -v "$(pwd)/firmware:/workspace:Z" -w /workspace docker.io/library/alpine:latest \
    sh -c "apk add --no-cache g++ && g++ -std=c++17 -Wall -Wextra tests/test_firmware.cpp -o tests/test_runner && ./tests/test_runner"
```

### 4.2 Python Schema Parity Tests
Verifies C++ struct definitions against the backend API JSON schema:
```bash
backend/.venv/bin/pytest firmware/tests/test_firmware_contract.py -v
```

---

## 5. Next Steps for Physical Hardware Integration

When the physical ESP32 board and sensor are selected:
1. Complete the checklist in [docs/hardware/hardware-selection.md](../docs/hardware/hardware-selection.md).
2. Create concrete driver classes implementing `ISensor` and `IAlertOutput`.
3. Configure board target and pins in Arduino IDE or PlatformIO.
4. Flash and test with physical hardware in an isolated bench environment.
