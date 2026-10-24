# HeatShield Bharat — Firmware

## Purpose

The firmware runs on an ESP32 microcontroller and is responsible for:

1. Reading environmental sensors (temperature, humidity, and related parameters).
2. Calculating local heat-index or heat-risk values on-device.
3. Triggering local alerts (buzzer, LED) when thresholds are exceeded.
4. Transmitting telemetry data to the backend API via Wi-Fi (HTTPS/JSON).
5. Buffering readings locally when the network is unavailable and uploading
   them when connectivity is restored.
6. Managing deep-sleep and power-saving modes for field deployment.

---

## ⚠ Hardware Confirmation Status

> **The hardware inventory is UNCONFIRMED.**
>
> No ESP32 board, sensor modules, or supporting components have been purchased
> or verified yet. No board-specific firmware or sensor drivers have been
> implemented.

The following information **must be confirmed** before firmware development
can begin:

### 1. ESP32 Board

- **Model:** *(e.g., ESP32-DevKitC V4, ESP32-S3, ESP32-C3, NodeMCU-32S)*
- **Flash size:** *(e.g., 4 MB, 8 MB, 16 MB)*
- **USB interface:** *(e.g., CP2102, CH340, native USB)*
- **Available GPIO pins:** *(mapped to sensor and alert connections)*

### 2. Environmental Sensors

- **Temperature/Humidity sensor model:** *(e.g., DHT22, BME280, SHT31, AHT20)*
- **Interface:** *(e.g., I²C, SPI, single-wire digital, analog)*
- **Accuracy and range:** *(check datasheet)*
- **Additional sensors:** *(UV index, barometric pressure, wind, etc.)*

### 3. Electrical Requirements

- **Operating voltage:** *(3.3 V logic? 5 V supply?)*
- **Power supply:** *(USB, battery, solar?)*
- **Pull-up resistors needed?**
- **Level shifters required?**

### 4. Alert Output

- **Buzzer type:** *(active or passive?)*
- **LED indicators:** *(count, colour, GPIO assignments)*

### 5. Development Toolchain

- **Framework:** Arduino for ESP32 *(planned, subject to change)*
- **IDE / Build tool:** Arduino IDE, PlatformIO, or ESP-IDF
- **Upload method:** USB serial
- **Libraries:** Sensor driver library, WiFi, HTTPClient, ArduinoJson

### 6. Offline Storage

- **Approach:** *(SPIFFS, LittleFS, SD card — depends on board flash size)*
- **Buffer capacity target:** *(hours of readings to retain offline)*

---

## Directory Structure (Planned)

```
firmware/
├── README.md           ← you are here
├── src/                # Main firmware source (created after hardware confirmation)
├── include/            # Header files
├── lib/                # Project-specific libraries
├── test/               # Firmware unit tests
├── platformio.ini      # PlatformIO config (if chosen)
└── secrets.h.example   # Template for Wi-Fi / API credentials
```

> Directories and source files will be created once the hardware is confirmed
> and the toolchain is set up.

---

## Getting Started (Future)

1. Confirm and document the hardware (see checklist above).
2. Install the chosen development toolchain (PlatformIO recommended).
3. Copy `secrets.h.example` to `secrets.h` and add your Wi-Fi credentials
   and backend API key. **Never commit `secrets.h`.**
4. Connect the ESP32 via USB.
5. Build and upload the firmware.

Detailed instructions will be added after the hardware is confirmed.
