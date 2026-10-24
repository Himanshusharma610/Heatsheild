# HeatShield Bharat — API Contracts

> **Status:** Proposed (Module 2). These contracts define the intended request
> and response schemas for the versioned REST API. No endpoints are implemented
> yet — implementation is planned for Module 3.
>
> All example payloads use **illustrative values only**. They are not actual
> hardware readings or real system data.

---

## 1. General Conventions

### Base URL

```
/api/v1
```

### Content Type

All request and response bodies use `application/json`.

### Authentication

Device and user authentication mechanisms are **TBD**. Until implemented:
- Device endpoints will expect an `Authorization` header (format TBD).
- Dashboard endpoints will expect a session token or JWT (format TBD).
- All contracts below note authentication expectations.

### Timestamp Format

All timestamps use **ISO 8601 with UTC timezone**:

```
2026-11-15T10:30:00Z
```

### Pagination

List endpoints that may return large result sets support cursor-based or
offset-based pagination:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 50 | Maximum items per page (max 200) |
| `offset` | integer | 0 | Number of items to skip |

Paginated responses include:

```json
{
  "data": [],
  "pagination": {
    "total": 1234,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

### Error Response Format

All error responses follow a consistent structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error description.",
    "details": [
      {
        "field": "relative_humidity_pct",
        "message": "Value must be between 0 and 100.",
        "value": 150.0
      }
    ]
  }
}
```

| Field | Type | Always Present | Description |
|---|---|---|---|
| `error.code` | string | Yes | Machine-readable error code |
| `error.message` | string | Yes | Human-readable summary |
| `error.details` | array | No | Field-level errors (validation) |

### Standard Error Codes

| HTTP Status | Error Code | Meaning |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed request |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | Authenticated but insufficient permissions |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Resource conflict (e.g., duplicate device_code) |
| 422 | `VALIDATION_ERROR` | Request body fails validation |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## 2. Health Check

### `GET /health`

**Purpose:** Verify the API server is running. Used by load balancers and
monitoring tools.

**Authentication:** None required.

**Response `200 OK`:**

```json
{
  "status": "healthy",
  "timestamp": "2026-11-15T10:30:00Z",
  "version": "0.1.0"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | `"healthy"` or `"degraded"` |
| `timestamp` | string | Server time (UTC, ISO 8601) |
| `version` | string | API version |

---

## 3. Devices

### `GET /api/v1/devices`

**Purpose:** List registered devices, optionally filtered by worksite or status.

**Authentication:** Required (dashboard user).

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `worksite_id` | UUID | No | — | Filter by worksite |
| `status` | string | No | — | Filter by device status |
| `is_active` | boolean | No | `true` | Include deactivated devices |
| `limit` | integer | No | 50 | Pagination limit |
| `offset` | integer | No | 0 | Pagination offset |

**Response `200 OK`:**

```json
{
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "device_code": "HS-WS01-D001",
      "worksite_id": "f0e1d2c3-b4a5-6789-0fed-cba987654321",
      "display_name": "Outdoor Sensor Alpha",
      "status": "online",
      "firmware_version": "0.1.0",
      "last_seen_at": "2026-11-15T10:30:00Z",
      "is_active": true,
      "created_at": "2026-10-24T08:00:00Z",
      "updated_at": "2026-11-15T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 5,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

---

### `POST /api/v1/devices`

**Purpose:** Register a new device.

**Authentication:** Required (supervisor or admin).

**Request Body:**

```json
{
  "device_code": "HS-WS01-D002",
  "worksite_id": "f0e1d2c3-b4a5-6789-0fed-cba987654321",
  "display_name": "Outdoor Sensor Beta"
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `device_code` | string | Yes | 1–100 chars, unique across all devices |
| `worksite_id` | UUID | Yes | Must reference an active worksite |
| `display_name` | string | No | Max 200 chars |

**Response `201 Created`:**

```json
{
  "data": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "device_code": "HS-WS01-D002",
    "worksite_id": "f0e1d2c3-b4a5-6789-0fed-cba987654321",
    "display_name": "Outdoor Sensor Beta",
    "status": "registered",
    "firmware_version": null,
    "last_seen_at": null,
    "is_active": true,
    "created_at": "2026-11-15T11:00:00Z",
    "updated_at": "2026-11-15T11:00:00Z"
  }
}
```

**Error Responses:**

| Status | Code | When |
|---|---|---|
| 409 | `CONFLICT` | `device_code` already exists |
| 422 | `VALIDATION_ERROR` | Missing required fields or invalid `worksite_id` |

---

## 4. Sensor Readings

### `POST /api/v1/readings`

**Purpose:** Ingest a sensor reading from a device. Supports idempotent retries
via the `(device_code, event_id)` pair.

**Authentication:** Required (device authentication).

**Request Body:**

```json
{
  "device_code": "HS-WS01-D001",
  "event_id": "evt-00042",
  "measured_at": "2026-11-15T10:30:00Z",
  "temperature_c": 38.5,
  "relative_humidity_pct": 72.3,
  "firmware_version": "0.1.0"
}
```

> ⚠ **Illustrative values only.** These are not actual hardware readings.

| Field | Type | Required | Validation |
|---|---|---|---|
| `device_code` | string | Yes | Must match a registered, active device |
| `event_id` | string | Yes | 1–100 chars; unique per device |
| `measured_at` | string (ISO 8601) | No | UTC timestamp from device clock; nullable |
| `temperature_c` | number | No | Nullable; `NUMERIC(6,2)` precision |
| `relative_humidity_pct` | number | No | Nullable; must be 0–100 if present |
| `firmware_version` | string | No | Max 50 chars |

**Response `201 Created` (new reading):**

```json
{
  "data": {
    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "event_id": "evt-00042",
    "measured_at": "2026-11-15T10:30:00Z",
    "received_at": "2026-11-15T10:30:05Z",
    "temperature_c": 38.5,
    "relative_humidity_pct": 72.3,
    "quality_status": "valid",
    "source_mode": "hardware",
    "firmware_version": "0.1.0",
    "created_at": "2026-11-15T10:30:05Z"
  }
}
```

**Response `200 OK` (duplicate — idempotent retry):**

If a reading with the same `(device_code, event_id)` already exists, the
existing reading is returned with `200 OK`. No new record is created.

```json
{
  "data": {
    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "event_id": "evt-00042",
    "received_at": "2026-11-15T10:30:05Z",
    "...": "..."
  },
  "deduplicated": true
}
```

**Error Responses:**

| Status | Code | When |
|---|---|---|
| 401 | `UNAUTHORIZED` | Missing or invalid device auth |
| 422 | `VALIDATION_ERROR` | Payload validation failure (e.g., humidity > 100) |
| 422 | `VALIDATION_ERROR` | Unknown `device_code` |

**Retry behaviour:**
- Firmware should retry on `5xx` and network timeouts.
- Firmware should **not** retry on `401` (auth failure) or `422` (validation failure).
- `200` responses indicate the reading was already ingested — safe to continue.

---

### `GET /api/v1/readings/latest`

**Purpose:** Get the most recent reading for each device, or for a specific device.

**Authentication:** Required (dashboard user).

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `device_id` | UUID | No | — | Filter to a specific device |
| `worksite_id` | UUID | No | — | Filter to a specific worksite |
| `quality_status` | string | No | — | Filter by quality status |

**Response `200 OK`:**

```json
{
  "data": [
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "device_code": "HS-WS01-D001",
      "event_id": "evt-00042",
      "measured_at": "2026-11-15T10:30:00Z",
      "received_at": "2026-11-15T10:30:05Z",
      "temperature_c": 38.5,
      "relative_humidity_pct": 72.3,
      "quality_status": "valid",
      "source_mode": "hardware",
      "firmware_version": "0.1.0"
    }
  ]
}
```

---

### `GET /api/v1/readings/history`

**Purpose:** Query historical readings for a device within a time range.

**Authentication:** Required (dashboard user).

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `device_id` | UUID | Yes | — | Target device |
| `start_time` | string (ISO 8601) | No | 24h ago | Start of time range (inclusive) |
| `end_time` | string (ISO 8601) | No | now | End of time range (inclusive) |
| `quality_status` | string | No | — | Filter by quality status |
| `limit` | integer | No | 50 | Pagination limit (max 200) |
| `offset` | integer | No | 0 | Pagination offset |

**Response `200 OK`:**

```json
{
  "data": [
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "event_id": "evt-00042",
      "measured_at": "2026-11-15T10:30:00Z",
      "received_at": "2026-11-15T10:30:05Z",
      "temperature_c": 38.5,
      "relative_humidity_pct": 72.3,
      "quality_status": "valid",
      "source_mode": "hardware",
      "firmware_version": "0.1.0"
    },
    {
      "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
      "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "event_id": "evt-00041",
      "measured_at": "2026-11-15T10:25:00Z",
      "received_at": "2026-11-15T10:25:03Z",
      "temperature_c": 37.8,
      "relative_humidity_pct": 71.1,
      "quality_status": "valid",
      "source_mode": "hardware",
      "firmware_version": "0.1.0"
    }
  ],
  "pagination": {
    "total": 288,
    "limit": 50,
    "offset": 0,
    "has_more": true
  },
  "query": {
    "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "start_time": "2026-11-14T10:30:00Z",
    "end_time": "2026-11-15T10:30:00Z"
  }
}
```

---

## 5. Alerts

### `GET /api/v1/alerts`

**Purpose:** List alerts, optionally filtered by device, worksite, status,
or severity.

**Authentication:** Required (dashboard user).

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `device_id` | UUID | No | — | Filter by device |
| `worksite_id` | UUID | No | — | Filter by worksite (via device) |
| `status` | string | No | — | Filter by alert status |
| `severity` | string | No | — | Filter by severity |
| `start_time` | string (ISO 8601) | No | 24h ago | Triggered after |
| `end_time` | string (ISO 8601) | No | now | Triggered before |
| `limit` | integer | No | 50 | Pagination limit |
| `offset` | integer | No | 0 | Pagination offset |

**Response `200 OK`:**

```json
{
  "data": [
    {
      "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
      "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "device_code": "HS-WS01-D001",
      "reading_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "alert_rule_id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
      "alert_rule_name": "High Temperature Warning",
      "event_type": "threshold_exceeded",
      "severity": "warning",
      "status": "triggered",
      "rule_version_snapshot": 2,
      "triggered_at": "2026-11-15T10:30:05Z",
      "acknowledged_at": null,
      "resolved_at": null
    }
  ],
  "pagination": {
    "total": 3,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

---

### `POST /api/v1/alerts/{id}/acknowledge`

**Purpose:** Acknowledge an active alert and optionally record the safety
action taken.

**Authentication:** Required (supervisor or admin).

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Alert ID |

**Request Body:**

```json
{
  "action_taken": "Workers moved to shaded rest area. Water distributed."
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `action_taken` | string | No | Max 2000 chars |

**Response `200 OK`:**

```json
{
  "data": {
    "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
    "status": "acknowledged",
    "acknowledged_at": "2026-11-15T10:35:00Z",
    "acknowledgement": {
      "id": "a7b8c9d0-e1f2-3456-abcd-567890123456",
      "actor_id": "b8c9d0e1-f2a3-4567-bcde-678901234567",
      "action_taken": "Workers moved to shaded rest area. Water distributed.",
      "acknowledged_at": "2026-11-15T10:35:00Z"
    }
  }
}
```

**Error Responses:**

| Status | Code | When |
|---|---|---|
| 404 | `NOT_FOUND` | Alert ID does not exist |
| 409 | `CONFLICT` | Alert is already `resolved` or `expired` |

---

## 6. Alert Rules

### `GET /api/v1/alert-rules`

**Purpose:** List configured alert rules.

**Authentication:** Required (supervisor or admin).

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `worksite_id` | UUID | No | — | Filter by worksite (includes global rules) |
| `is_enabled` | boolean | No | — | Filter by enabled status |
| `severity` | string | No | — | Filter by severity |
| `limit` | integer | No | 50 | Pagination limit |
| `offset` | integer | No | 0 | Pagination offset |

**Response `200 OK`:**

```json
{
  "data": [
    {
      "id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
      "name": "High Temperature Warning",
      "worksite_id": "f0e1d2c3-b4a5-6789-0fed-cba987654321",
      "metric": "temperature_c",
      "operator": "gte",
      "threshold_value": 40.00,
      "threshold_params": null,
      "severity": "warning",
      "is_enabled": true,
      "rule_version": 2,
      "created_at": "2026-10-30T09:00:00Z",
      "updated_at": "2026-11-10T14:00:00Z"
    },
    {
      "id": "a7b8c9d0-e1f2-3456-bcde-567890123456",
      "name": "Extreme Heat Emergency",
      "worksite_id": null,
      "metric": "temperature_c",
      "operator": "gte",
      "threshold_value": 48.00,
      "threshold_params": null,
      "severity": "emergency",
      "is_enabled": true,
      "rule_version": 1,
      "created_at": "2026-10-30T09:00:00Z",
      "updated_at": "2026-10-30T09:00:00Z"
    }
  ],
  "pagination": {
    "total": 2,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

> ⚠ **Threshold values above are illustrative.** Appropriate thresholds must be
> determined with relevant occupational safety guidance. These examples do not
> claim compliance with any standard.

---

## 7. Heat-Risk Data Contract

### Separation of Concerns

The system maintains a strict separation between five data layers:

| Layer | Stored In | Set By | Example |
|---|---|---|---|
| **1. Raw measurements** | `sensor_readings` | Device / backend ingestion | `temperature_c = 38.5`, `relative_humidity_pct = 72.3` |
| **2. Data quality** | `sensor_readings.quality_status` | Backend validation | `valid`, `suspect`, `invalid`, `missing` |
| **3. Calculated indicators** | Future: `computed_indicators` table or API response field | Backend risk engine (Module 6+) | Heat index = 45.2 (formula TBD) |
| **4. Risk classification** | Future: mapped from indicator value | Backend risk engine (Module 6+) | `warning` level (thresholds TBD) |
| **5. Alert events** | `alerts` | Backend alert engine | Threshold exceeded → alert triggered |

### Key Constraints

- **Temperature and humidity alone do not constitute a WBGT measurement.**
  Any computed heat-stress indicator must document:
  - The specific formula used (e.g., Steadman heat index, simplified WBGT approximation).
  - The units of the result.
  - The assumptions made (e.g., shade, wind speed, solar radiation defaults).
  - The input requirements (which sensor readings are needed).
  - The limitations (e.g., valid input ranges, accuracy compared to full WBGT).
  - The rule version that produced the calculation.

- **Risk thresholds are not selected in this module.** The precise thresholds
  for `warning`, `critical`, and `emergency` classifications will be defined
  in the dedicated risk-engine module after:
  - Confirming available sensor inputs.
  - Reviewing relevant occupational safety guidance.
  - Selecting and documenting the heat-stress formula.

- **No medical claims.** The system does not diagnose heatstroke or establish
  that a worker is medically unsafe. It provides environmental monitoring data
  and configurable alerts for operational decision-making.

- **Calculated values are always derived, never stored as raw measurements.**
  The `sensor_readings` table contains only measured data and quality metadata.
  Computed indicators are stored separately or returned as API response fields
  with explicit formula identification.

---

## 8. Cross-References

- [System Architecture](system-architecture.md)
- [Data Flow Specification](data-flow.md)
- [Database Design](database-design.md)
- [Architecture Decisions](../decisions/architecture-decisions.md)
- [Sensor Reading JSON Schema](../contracts/sensor-reading.schema.json)
