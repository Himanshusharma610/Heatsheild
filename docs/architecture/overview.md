# HeatShield Bharat — Architecture Overview

> **Status:** Proposed. This architecture is subject to refinement in later
> modules as implementation progresses and hardware is confirmed.

---

## System Overview

HeatShield Bharat is a multi-layer IoT system that monitors environmental heat
conditions, computes heat-risk indices, and delivers alerts through both local
hardware and a web dashboard.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FIELD DEPLOYMENT                            │
│                                                                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│   │  Temp/Humid  │    │   ESP32      │    │  Buzzer/LED  │         │
│   │   Sensor     │───►│  Firmware    │───►│  Local Alert │         │
│   └──────────────┘    └──────┬───────┘    └──────────────┘         │
│                              │                                      │
│                              │ Wi-Fi (HTTPS/JSON)                   │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         CLOUD / SERVER                               │
│                                                                      │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│   │   FastAPI     │───►│  PostgreSQL  │◄───│   Alembic    │          │
│   │   Backend     │    │   Database   │    │  Migrations  │          │
│   └──────┬───────┘    └──────────────┘    └──────────────┘          │
│          │                                                           │
│          │ REST API (JSON)                                           │
│          ▼                                                           │
│   ┌──────────────┐                                                   │
│   │    React      │                                                  │
│   │   Dashboard   │                                                  │
│   └──────────────┘                                                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### 1. Physical Sensors

- Measure temperature, humidity, and (potentially) other environmental
  parameters.
- Connected to the ESP32 via I²C, SPI, or digital GPIO (interface depends on
  the confirmed sensor model).
- **Hardware status:** Unconfirmed.

### 2. ESP32 Firmware

- Reads sensor data at configurable intervals.
- Computes a local heat-index value for immediate on-device alerting.
- Triggers local alerts (buzzer, LED) when configurable thresholds are exceeded
  — this works even without network connectivity.
- Formats telemetry as JSON and transmits it to the backend via an
  authenticated HTTPS POST endpoint.
- Buffers readings in local flash storage (SPIFFS / LittleFS) when the network
  is unavailable, and uploads buffered data when connectivity is restored.
- Manages power-saving modes (deep sleep) for battery-powered deployments.

### 3. FastAPI Backend

- Exposes a versioned REST API (`/api/v1/...`).
- **Telemetry ingestion endpoint:** Receives, validates, and stores sensor
  readings. Authenticates the sending device.
- **Data query endpoints:** Serve current and historical readings to the
  dashboard.
- **Alert processing:** Evaluates server-side alert rules against incoming data
  (e.g., sustained high heat-index over multiple readings).
- **Alert delivery:** Sends notifications via configured channels (email,
  webhook, push — details TBD).
- Clearly labels simulated data when used during development.

### 4. PostgreSQL Database

- Persists all sensor readings, device metadata, alert rules, and alert
  history.
- Managed through SQLAlchemy models and Alembic migrations.
- Timestamps stored in UTC.

### 5. React Dashboard

- Displays current conditions and historical trends (charts, tables, maps).
- Shows active alerts and their resolution status.
- Provides device management views.
- Communicates with the backend exclusively through the versioned REST API.
- Runs as a single-page application (SPA) built with Vite.

---

## Local Alerts vs. Server-Side Alerts

| Aspect | Local Alert (Firmware) | Server-Side Alert (Backend) |
|---|---|---|
| Trigger | Single reading exceeds threshold | Rules evaluated over multiple readings |
| Latency | Immediate (milliseconds) | Depends on telemetry interval |
| Output | Buzzer, LED | Dashboard notification, email, webhook |
| Network required | No | Yes |
| Configurability | Hardcoded or flash-stored thresholds | Database-stored rules, editable via API |

Both mechanisms are complementary: local alerts ensure safety even when
offline, while server-side alerts enable richer analysis and notification.

---

## Offline Operation

The firmware is designed to function independently of the network:

1. Sensors are read and local heat-index is calculated regardless of
   connectivity.
2. Local alerts fire immediately based on on-device thresholds.
3. Readings are buffered in flash storage when the network is down.
4. On reconnection, buffered readings are uploaded in chronological order.
5. The backend timestamps reflect the original reading time, not the upload
   time.

---

## Data Flow Summary

1. **Sensor → ESP32:** Raw analog/digital reading.
2. **ESP32 → Local alert:** Immediate threshold check.
3. **ESP32 → Backend API:** Authenticated JSON telemetry POST.
4. **Backend → Database:** Validated reading stored with UTC timestamp.
5. **Backend → Alert engine:** Server-side rule evaluation.
6. **Backend → Dashboard:** REST API response (current + historical data).
7. **Backend → Notification:** Alert delivery via configured channels.

---

## Security Considerations (Planned)

- Device authentication via API key or token (mechanism TBD).
- HTTPS for all telemetry transmission.
- Backend authentication for dashboard users (mechanism TBD).
- Secrets never stored in version control.
- Environment-specific configuration via `.env` files.

---

## Next Steps

- Confirm hardware and update sensor/board details.
- Design the PostgreSQL schema (Module 2).
- Implement the telemetry API (Module 3).
- Scaffold the React dashboard (Module 4).
- Develop firmware after hardware arrives (Module 5).
