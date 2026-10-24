# HeatShield Bharat — Hardware Selection & Physical Integration Guide

## Status
- **Current Hardware Phase:** `UNCONFIRMED` (Module 5 Scaffolding)
- **Physical Procurement:** No physical hardware has been purchased or received.
- **Firmware State:** Hardware Abstraction Layer (HAL) implemented with safe unconfigured defaults.

---

## 1. Executive Summary & Purpose

This document provides the technical checklist, interface specifications, and physical integration steps required to transition the **HeatShield Bharat** firmware from its current hardware-independent scaffolding state (Module 5) into a physical, field-deployable embedded prototype.

Because physical components have not yet been procured, all GPIO pins, communication buses (I2C/OneWire), sensor drivers, and peripheral pinouts remain **`UNCONFIRMED`**. The firmware scaffolding isolates these details behind clean C++ interfaces (`ISensor`, `IAlertOutput`, `ITelemetryPublisher`), guaranteeing that missing, corrupted, or unconfigured states safely evaluate to `ALERT_LEVEL_UNKNOWN` without masking hazards.

---

## 2. Deliberately Deferred Decisions

The following architectural and physical decisions are deliberately deferred until hardware arrives:

| Decision | Current Scaffolding State | Reason for Deferral |
| :--- | :--- | :--- |
| **Exact ESP32 Board & MCU** | `UNCONFIRMED` | Form factor, onboard antenna, USB-UART vs USB-JTAG, and power consumption depend on final budget and enclosure design. |
| **Sensor Model & Breakout** | `UNCONFIRMED` | Precision, bus protocol (I2C vs OneWire), calibration stability, and supply chain availability must be evaluated. |
| **GPIO Pin Allocations** | `UNCONFIRMED` | Pinout varies widely between ESP32 devkits (ESP32-WROOM-32, ESP32-S3-DevKitC-1, ESP32-C3-SuperMini). Assigning pins prematurely risks electrical conflicts with bootstrap pins or SPI flash. |
| **Sensor Driver Library** | `UNCONFIRMED` | Driver selection must strictly correspond to verified sensor silicon revision and tested library stability. |
| **Actuator Pinouts (Buzzer/LED)** | `UNCONFIRMED` | Electrical driving requirements (current limits, active-high vs active-low, transistor buffers) must be matched to selected indicators. |
| **Telemetry Transport** | `UNCONFIRMED` | Wi-Fi vs BLE vs cellular/LoRaWAN trade-off depends on worksite infrastructure. |

---

## 3. Hardware Integration Checklist

The following parameters must be confirmed and documented prior to compiling concrete physical drivers:

```markdown
### Hardware Confirmation Checklist (Status: UNCONFIRMED)

- [ ] 1. Exact ESP32 Board Name & Revision: `UNCONFIRMED`
      (e.g., Espressif ESP32-DevKitC-32E v4 / NodeMCU-32S / ESP32-S3-DevKitC-1)
- [ ] 2. Board Variant & MCU: `UNCONFIRMED`
      (e.g., ESP32-D0WD-V3 dual-core Xtensa LX6 @ 240 MHz / ESP32-S3 / ESP32-C3 RISC-V)
- [ ] 3. Exact Temperature/Humidity Sensor Model: `UNCONFIRMED`
      (e.g., Sensirion SHT31-DIS-B / Bosch Sensortec BME280 / Aosong DHT22 / AM2302)
- [ ] 4. Sensor Breakout Board Version: `UNCONFIRMED`
      (e.g., Adafruit SHT31-D #2857 / SparkFun BME280 / generic module with onboard LDO & pull-ups)
- [ ] 5. Interface Type: `UNCONFIRMED`
      (e.g., I2C bus @ 100 kHz / OneWire digital single-bus)
- [ ] 6. Voltage & Logic-Level Compatibility: `UNCONFIRMED`
      (ESP32 GPIOs are 3.3V logic ONLY. 5V sensors require logic level shifting or 3.3V breakout LDO)
- [ ] 7. Required Arduino Libraries & Exact Versions: `UNCONFIRMED`
      (e.g., `Adafruit SHT31 Library@v2.2.2`, `Adafruit BusIO@v1.16.1`)
- [ ] 8. Pin Assignments & Physical Wiring: `UNCONFIRMED`
      - SDA Pin: `UNCONFIRMED` (avoid strapping pins GPIO 0, 2, 12, 15)
      - SCL / OneWire Pin: `UNCONFIRMED`
      - Alert Output (Buzzer): `UNCONFIRMED`
      - Alert Output (Visual LED): `UNCONFIRMED`
- [ ] 9. Required Sampling Interval & Warm-up Time: `UNCONFIRMED`
      (Datasheet review needed: e.g., DHT22 requires >= 2000 ms between reads; SHT31 supports 1000 ms periodic)
- [ ] 10. Available Local Alert Outputs & Electrical Requirements: `UNCONFIRMED`
      (Active piezoelectric buzzer: check max current draw <= 12 mA, or use NPN transistor switch like 2N2222)
```

---

## 4. Sensor Candidate Trade-Off Analysis

| Sensor Model | Interface | Supply Voltage | Temp Accuracy | Humidity Accuracy | Min Interval | Scaffolding Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Sensirion SHT31-D** | I2C (0x44/0x45) | 2.4V – 5.5V | ±0.2 °C | ±2.0% RH | 100 ms | **Recommended Candidate**: High accuracy, industrial calibration, reliable I2C CRC8 checksums, onboard heater for condensation. |
| **Bosch BME280** | I2C (0x76/0x77) / SPI | 1.8V – 3.6V | ±0.5 °C | ±3.0% RH | 100 ms | **Strong Candidate**: Includes barometric pressure, very stable, standard I2C. |
| **AHT20** | I2C (0x38) | 2.0V – 5.5V | ±0.3 °C | ±2.0% RH | 500 ms | **Cost-Effective Alternative**: Good precision, low power, simple I2C. |
| **DHT22 / AM2302** | OneWire (Proprietary) | 3.3V – 5.5V | ±0.5 °C | ±2.0% – 5.0% RH | 2000 ms | **Discouraged for Mission-Critical**: High timing sensitivity, frequent read timeouts, slow 0.5 Hz polling limit. |

---

## 5. Electrical & Schematic Precautions

When physical wiring is configured, adhere to the following safety rules:
1. **ESP32 3.3V Logic Tolerance:** The ESP32 is strictly a 3.3V CMOS device. Supplying 5V to any GPIO pin will degrade or permanently damage the SoC. Ensure breakout boards incorporate onboard regulators or level shifters if powered from 5V (VBUS).
2. **I2C Pull-Up Resistors:** Dedicated I2C lines (`SDA`, `SCL`) require pull-up resistors (typically 4.7 kΩ to 3.3V). Verify whether the selected breakout board includes these resistors.
3. **Strapping Pins:** Do NOT assign sensors or alert outputs to ESP32 strapping pins:
   - `GPIO 0`: Bootloader mode trigger.
   - `GPIO 2`: Flashing mode bootstrap.
   - `GPIO 12`: Flash voltage select (MTDI).
   - `GPIO 15`: Boot message output (MTDO).
4. **Current Sink/Source Limits:** ESP32 GPIOs should not source more than 12 mA continuously. Piezo buzzers and high-brightness warning LEDs must be driven via a transistor switch (e.g. NPN 2N2222 / MOSFET 2N7002) powered from the 3.3V or 5V rail.

---

## 6. How to Run Available Host Tests

All firmware business logic (reading contracts, validation limits, fail-safe alert states, and hysteresis) is completely decoupled from the Arduino hardware runtime and can be tested on any host computer.

### Method 1: Using the Automated Runner Script
The repository provides `firmware/tests/run_tests.sh`, which automatically detects native `g++` or falls back to a rootless Podman/Docker container:

```bash
# From workspace root:
./firmware/tests/run_tests.sh
```

### Method 2: Manual Containerized Build (Podman/Docker)
```bash
podman run --rm \
    -v "$(pwd)/firmware:/workspace:Z" \
    -w /workspace \
    docker.io/library/alpine:latest \
    sh -c "apk add --no-cache g++ && g++ -std=c++17 -Wall -Wextra tests/test_firmware.cpp -o tests/test_runner && ./tests/test_runner"
```

### Method 3: Contract Parity Test (Pytest)
Validates that the C/C++ struct in `reading_types.h` mirrors `docs/contracts/sensor-reading.schema.json`:

```bash
backend/.venv/bin/pytest firmware/tests/test_firmware_contract.py -v
```

---

## 7. Configuration & Build After Hardware Selection

Once physical components are confirmed:

1. **Implement Concrete Sensor Class:**
   Create `firmware/heatshield/sensor_sht31.h` (or respective driver) implementing `ISensor`:
   ```cpp
   #include "sensor_interface.h"
   #include <Adafruit_SHT31.h>

   class SHT31Sensor : public ISensor {
       Adafruit_SHT31 _sht;
   public:
       bool begin() override { return _sht.begin(0x44); }
       bool read(EnvironmentalReading& r) override {
           float t = _sht.readTemperature();
           float h = _sht.readHumidity();
           if (isnan(t) || isnan(h)) return false;
           r.has_temperature = true;
           r.temperature_c = t;
           r.has_humidity = true;
           r.relative_humidity_pct = h;
           r.sensor_status = SENSOR_STATUS_OK;
           r.source_mode = SOURCE_MODE_HARDWARE;
           return true;
       }
       SensorStatus get_status() const override { return SENSOR_STATUS_OK; }
       const char* get_driver_name() const override { return "SHT31 (I2C 0x44)"; }
   };
   ```

2. **Implement Concrete Alert Output:**
   Create `firmware/heatshield/alert_gpio_output.h` implementing `IAlertOutput` using confirmed GPIO pins:
   ```cpp
   class GpioAlertOutput : public IAlertOutput {
       uint8_t _buzzer_pin;
       uint8_t _led_pin;
   public:
       GpioAlertOutput(uint8_t buzzer_pin, uint8_t led_pin)
           : _buzzer_pin(buzzer_pin), _led_pin(led_pin) {
           pinMode(_buzzer_pin, OUTPUT);
           pinMode(_led_pin, OUTPUT);
       }
       void update(AlertLevel level) override {
           // Drive buzzer and LED according to confirmed safety policy
       }
       const char* get_name() const override { return "GPIO Buzzer/LED Output"; }
   };
   ```

3. **Compile in Arduino IDE / Arduino CLI:**
   - Open `firmware/heatshield/heatshield.ino` in Arduino IDE 2.x.
   - Select Board: `ESP32 Dev Module` (or confirmed variant).
   - Install required sensor library via Library Manager.
   - Compile and flash via USB-UART bridge.

---

## 8. Test Execution Status (Module 5 Verification)

| Test Category | Target Component | Execution Environment | Status | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Sensor Abstraction** | `UnconfiguredSensor` | Host C++ (Alpine Container / g++) | Executed | **PASS** (16/16) |
| **Diagnostic Mock** | `DiagnosticSimulatedSensor` | Host C++ (Alpine Container / g++) | Executed | **PASS** |
| **Numerical Sanity** | `isnan()`, `isinf()` handling | Host C++ (Alpine Container / g++) | Executed | **PASS** |
| **Plausibility Bounds**| Out-of-bounds Temp & Humidity | Host C++ (Alpine Container / g++) | Executed | **PASS** |
| **Missing Data Safety**| Null Temp/Hum -> Unknown Alert | Host C++ (Alpine Container / g++) | Executed | **PASS** (Never green) |
| **Thresholds & Hysteresis**| Safe / Caution / Danger state | Host C++ (Alpine Container / g++) | Executed | **PASS** |
| **Telemetry Decoupling**| `UnconfiguredTelemetryPublisher` | Host C++ (Alpine Container / g++) | Executed | **PASS** |
| **API Contract Parity** | `reading_types.h` vs JSON schema | Host Python 3.14 (Pytest) | Executed | **PASS** (5/5) |
| **Physical I2C Bus** | Physical SHT31 / BME280 | Physical Hardware | **BLOCKED** | Hardware pending selection |
| **Physical GPIO Pulse** | Physical Piezo Buzzer / LED | Physical Hardware | **BLOCKED** | Hardware pending selection |
| **Wi-Fi Telemetry Link**| ESP32 802.11b/g/n Radio | Physical Hardware | **BLOCKED** | Hardware pending selection |
