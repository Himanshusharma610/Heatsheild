# HeatShield Bharat — Backend Service

The backend service for **HeatShield Bharat**, an IoT-based environmental heat-monitoring and early-warning system.

> **Current Status (Module 12):** Foundational FastAPI application, environment configuration, PostgreSQL database layer (SQLAlchemy 2.0 ORM models, Alembic migrations, persistence repositories), health/readiness probes, authenticated telemetry ingestion (`POST /api/v1/readings`), Module 7 Heat-Risk Calculation Engine, Module 8 Alert Rules & Alert Lifecycle Management, Module 11 Historical Telemetry Queries & Analytics, and **Module 12 Human-User Authentication & Role-Based Access Control (RBAC)** featuring Argon2id password hashing, signed JWT Bearer access tokens, administrative user provisioning (`python -m app.cli.provision_admin`), strict credential isolation between IoT devices and human users, and server-side RBAC across all monitoring and alert endpoints.
>
> **Important Note on Limitations:** HeatShield Bharat provides environmental screening indicators and decision-support notifications for worksite supervisors. It does not provide medical diagnoses, predict individual heatstroke or thermal strain, or certify occupational safety compliance. Physical ESP32 microcontrollers and sensors remain unpurchased.


---

## Technical Specifications

- **Language:** Python 3.11+ (verified on Python 3.14)
- **Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Database Engine:** PostgreSQL 15+
- **Database Driver:** `psycopg2-binary`
- **ORM:** SQLAlchemy 2.0
- **Migrations:** Alembic
- **Configuration:** Pydantic Settings (environment-driven)
- **Testing:** Pytest with HTTPX and SQLAlchemy session fixtures

---

## Directory Structure

```text
backend/
├── alembic.ini               # Alembic configuration (no credentials hardcoded)
├── migrations/               # Alembic database migrations
│   ├── env.py                # Dynamic database URL injection & metadata configuration
│   ├── script.py.mako        # Migration template
│   └── versions/
│       └── 0001_initial_schema.py # Initial baseline migration (8 entities)
├── app/
│   ├── __init__.py           # Package version and metadata
│   ├── main.py               # Application factory create_app() & ASGI entrypoint
│   ├── config.py             # Typed Settings model with Pydantic Settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py         # Liveness (/health) and live readiness (/ready) probes
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── alerts.py     # Module 8: Alert listing, acknowledge, resolve, and rule CRUD
│   │       ├── readings.py   # Module 6 & 7: Telemetry ingestion & heat index calculation
│   │       └── router.py     # Versioned router aggregation (/api/v1)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py     # Custom exceptions and centralized error handlers
│   │   └── user_auth.py      # Module 8: Supervisor role-based authorization dependency
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py           # SQLAlchemy DeclarativeBase
│   │   └── session.py        # Engine builder, session factory, get_db, and ping check
│   ├── models/
│   │   ├── __init__.py       # Exports all 8 models
│   │   ├── alert.py          # AlertRule, Alert, AlertAcknowledgement
│   │   ├── audit.py          # AuditLog (append-only)
│   │   ├── device.py         # Device
│   │   ├── reading.py        # SensorReading
│   │   ├── user.py           # User (safe repr without password hash)
│   │   └── worksite.py       # Worksite
│   ├── repositories/
│   │   ├── __init__.py       # Exports repository functions
│   │   ├── alert.py          # Alert rules and event data access
│   │   ├── device.py         # Device registration and heartbeat data access
│   │   ├── reading.py        # Time-series sensor reading persistence & history
│   │   └── worksite.py       # Worksite CRUD and soft-deactivation
│   ├── schemas/
│   │   ├── __init__.py       # Schema exports
│   │   ├── alert.py          # Module 8: Alert and alert-rule request/response schemas
│   │   ├── common.py         # ErrorResponse and ErrorDetail schemas
│   │   ├── health.py         # HealthResponse and ReadyResponse schemas
│   │   ├── heat_risk.py      # Module 7: Heat-risk calculation schemas
│   │   └── telemetry.py      # Module 6: Telemetry ingestion schemas
│   └── services/
│       ├── alert_engine.py   # Module 8: Deterministic rule evaluation, deduplication, lifecycle
│       ├── heat_index.py     # Module 7: NOAA/NWS Rothfusz polynomial & Steadman simple equation
│       └── telemetry.py      # Module 6: Ingestion verification, quality checks, alert trigger
├── tests/
│   ├── conftest.py           # Test fixtures and isolated configuration
│   ├── test_alert_engine.py  # Module 8: Unit & API tests for rules, deduplication, lifecycle
│   ├── test_app.py           # Tests for factory, routing, CORS, errors, and settings
│   ├── test_db_readiness.py  # Tests for database readiness probe (connected, unavailable, etc.)
│   ├── test_health.py        # Tests for /health and /ready endpoints
│   ├── test_heat_index.py    # Module 7: Verification against NOAA reference data
│   ├── test_models.py        # Unit tests for ORM models and constraints
│   ├── test_postgres_integration.py # Real PostgreSQL 15 integration tests
│   ├── test_readings_ingestion.py # Module 6: Telemetry authentication, deduplication, quality
│   └── test_repositories.py  # Unit tests for repository functions
├── .env.example              # Template environment configuration
├── requirements.txt          # Pinned/constrained Python dependencies
└── README.md                 # This documentation
```

---

## Database Architecture (8 Entities)

All models mirror the Module 2 architectural specification:

1. **`worksites`** — Monitored physical locations (`is_active` soft-deletion).
2. **`devices`** — Physical ESP32 sensor nodes (`RESTRICT` foreign key from worksites).
3. **`sensor_readings`** — Environmental telemetry with deduplication `UNIQUE (device_id, event_id)`.
4. **`alert_rules`** — Configurable metric thresholds with rule versioning.
5. **`alerts`** — Generated incidents with independent severity (`info`→`emergency`) and status (`triggered`→`resolved`).
6. **`alert_acknowledgements`** — Documented safety action audit trails.
7. **`users`** — Supervisor and administrator accounts (passwords never exposed).
8. **`audit_logs`** — Append-only accountability log.

---

## Local Development Setup

### 1. Prerequisites

- Python 3.11 or higher
- PostgreSQL 15+ (local service, container, or remote development instance)

### 2. Create and Activate Virtual Environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

*(On Windows PowerShell: `.venv\Scripts\Activate.ps1`)*

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Local PostgreSQL Database

If using local PostgreSQL:

```sql
-- Connect via psql as postgres superuser
CREATE USER heatshield_dev WITH PASSWORD 'your_secure_password';
CREATE DATABASE heatshield_dev OWNER heatshield_dev;
GRANT ALL PRIVILEGES ON DATABASE heatshield_dev TO heatshield_dev;
```

Or using Podman / Docker:

```bash
podman run --rm -d --name heatshield_dev_pg \
  -e POSTGRES_USER=heatshield_dev \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=heatshield_dev \
  -p 5432:5432 docker.io/library/postgres:15-alpine
```

### 5. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` to configure your local connection URL:

```env
DATABASE_URL=postgresql://heatshield_dev:your_secure_password@localhost:5432/heatshield_dev
```

> **Security Rule:** Never commit the `.env` file or passwords to source control.

---

## Database Migrations (Alembic)

All migration commands read the database connection dynamically from your environment (passwords are never saved in `alembic.ini`).

### Inspect Migration History

```bash
alembic history
```

### Show Current Revision

```bash
alembic current
```

### Apply Migrations (Upgrade to Latest)

```bash
alembic upgrade head
```

### Rollback Previous Migration

> [!WARNING]
> Downgrading drops tables and associated data created by that revision. Only perform on development/test databases.

```bash
alembic downgrade -1
```

### Offline SQL Preview (Dry Run)

Generate static SQL without connecting to the database:

```bash
alembic upgrade --sql head
```

---

## Running the Application

From `backend/`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or:

```bash
python -m app.main
```

Interactive documentation:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Telemetry Ingestion API (Module 6)

### `POST /api/v1/readings`

Ingests environmental telemetry emitted by registered ESP32 sensor nodes.

#### Authentication
Requests must include a valid pre-shared device token in either the `X-Device-Token` header or `Authorization: Bearer <token>` header:
```bash
-H "X-Device-Token: your-device-secret-token"
# OR
-H "Authorization: Bearer your-device-secret-token"
```
The backend hashes the incoming token with SHA-256 and validates it against `devices.api_key_hash` using constant-time comparison. Unauthenticated or invalid requests return a generic `401 Unauthorized` response.

#### Provisioning a Development Test Device
To configure a test device for local development:
```python
from app.db.session import get_session_factory
from app.repositories.device import register_device, hash_device_token

session = get_session_factory()()
device = register_device(
    session=session,
    device_code="HS-DEV-001",
    worksite_id=your_worksite_id,
    display_name="Dev Bench ESP32",
    raw_token="dev-secret-token-12345",  # Automatically hashed and stored in api_key_hash
)
session.commit()
```

#### Example Ingestion Request
```bash
curl -X POST "http://localhost:8000/api/v1/readings" \
  -H "Content-Type: application/json" \
  -H "X-Device-Token: dev-secret-token-12345" \
  -d '{
    "device_code": "HS-DEV-001",
    "event_id": "evt-00001",
    "measured_at": "2026-10-24T22:15:00Z",
    "temperature_c": 38.5,
    "relative_humidity_pct": 65.0,
    "firmware_version": "0.1.0",
    "source_mode": "hardware"
  }'
```

#### Responses & Status Codes

| Status Code | Response Type | Description |
| :--- | :--- | :--- |
| **`201 Created`** | `ReadingResponse` | New reading successfully persisted. |
| **`200 OK`** | `ReadingDeduplicatedResponse` | Idempotent duplicate: event ID was previously recorded with identical measurements (`"deduplicated": true`). Safe for device to advance sequence counter. |
| **`401 Unauthorized`** | `ErrorResponse` | Missing token, invalid token, inactive device, or unregistered device code. |
| **`409 Conflict`** | `ErrorResponse` | Event ID collision: the event was already recorded with conflicting measurement data. |
| **`422 Validation Error`** | `ErrorResponse` | Missing required fields (`device_code`, `event_id`), humidity > 100 or < 0, or non-finite numbers (NaN/Inf). |
| **`503 Service Unavailable`** | `ErrorResponse` | Database persistence failure. Reading was rolled back. |

#### Data Quality Classification Policy
All readings are persisted with an evaluated `quality_status`:
- **`valid`**: Measurements present, physically plausible, and timestamp within acceptable drift window.
- **`suspect`**: Extreme ambient thermal range (-20°C to -40°C or 70°C to 85°C), future clock drift > 10 minutes, or uncalibrated historical RTC timestamp (< 2020).
- **`invalid`**: Non-finite float, extreme physical impossibility (< -40°C or > 85°C), or future timestamp drift > 24 hours.
- **`missing`**: Both temperature and humidity are absent (null).

---

## Heat-Risk Calculation Engine (Module 7)

### `POST /api/v1/readings/calculate-heat-index`

Evaluates the authoritative **National Weather Service (NWS) / NOAA Heat Index** deterministically from ambient temperature and humidity inputs, returning full explainability metadata.

For detailed mathematical formulations, coefficient tables, and scientific limitations, see:
👉 [Heat-Risk Calculation Method Specification](../docs/architecture/heat-risk-method.md)

#### Example Request
```bash
curl -X POST "http://localhost:8000/api/v1/readings/calculate-heat-index" \
  -H "Content-Type: application/json" \
  -d '{
    "temperature_c": 38.5,
    "relative_humidity_pct": 65.0,
    "quality_status": "valid"
  }'
```

#### Example Response (`200 OK`)
```json
{
  "status": "valid",
  "indicator_name": "heat_index",
  "value_c": 56.4,
  "value_f": 133.5,
  "unit": "celsius",
  "method": "NWS_ROTHFUSZ_1990",
  "method_version": "1.0.0",
  "equation_applied": "rothfusz_standard",
  "input_temperature_c": 38.5,
  "input_temperature_unit": "celsius",
  "input_relative_humidity_pct": 65.0,
  "input_humidity_unit": "percent",
  "informational_screening_level": "extreme_danger",
  "custom_classification": null,
  "limitations": [
    "Heat Index is an environmental screening indicator, NOT Wet Bulb Globe Temperature (WBGT).",
    "Assumes shade, light wind (approx. 5 knots / 2.5 m/s), standard atmospheric pressure, and typical light clothing.",
    "Exposure to direct, intense sunlight can increase apparent heat stress by up to 8°C (15°F).",
    "Does NOT account for personal metabolic workload, PPE encapsulation, hydration, age, acclimatization, or health conditions.",
    "Does NOT provide clinical medical diagnosis, heatstroke prediction, or official occupational compliance certification."
  ],
  "notes": "Evaluated via standard full Rothfusz 9-term polynomial.",
  "calculated_at": "2026-10-24T22:20:00Z"
}
```

#### Operating Domain & Status Outcomes
- **`valid`**: Input is within the supported domain (20°C to 55°C, 0% to 100% RH).
- **`out_of_domain`**: Temperature is below 20°C (68°F) or above 55°C (131°F). Returns `value_c: null` and `screening_level: "unavailable"`.
- **`missing_data`**: One or both inputs are missing (`null`). Never defaults to zero.
- **`invalid_input`**: Non-finite float (NaN/Inf), impossible temperature outside [-50°C, 100°C], or humidity outside [0, 100].
- **`invalid_quality`**: Upstream reading carries an `invalid` quality classification.
- **`stale`**: Reading timestamp exceeds freshness limits or `is_stale=True`. Returns `value_c: null` and `screening_level: "unavailable"`.
- **`suspect_quality`**: Evaluated normally, but flags `status: "suspect_quality"` with an audit note.

---

## Alert Rules & Alert Lifecycle Management (Module 8)

The backend provides an auditable, deterministic alert engine that evaluates incoming telemetry readings against explicitly configured threshold rules, records incidents, enforces episode deduplication, and manages supervisor acknowledgement workflows.

For architectural details, lifecycle state machine diagrams, and deduplication invariants, see:
👉 [Alert Lifecycle & Deduplication Specification](../docs/architecture/alert-lifecycle.md)

### Safety Declarations
- **Decision Support Only:** Alerts are operational decision-support notifications for worksite supervisors. They **must not** be presented as medical diagnoses or heatstroke predictions.
- **Provisional Development Thresholds:** Thresholds (such as Heat Index $\ge 41^\circ\text{C}$ for Warning or $\ge 54^\circ\text{C}$ for Critical) are provisional development defaults and are not officially approved Indian occupational safety regulations.
- **Physical Hardware Unconfirmed:** ESP32 microcontrollers and physical sensors are unpurchased. Backend alert processing requires active internet/network connectivity.

### Endpoints Overview

| Method | Endpoint | Authorization | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/alerts` | Authenticated | List alerts with status, severity, worksite, device filtering & pagination. |
| `POST` | `/api/v1/alerts/{alert_id}/acknowledge` | Supervisor / Admin | Acknowledge active alert with required `action_taken` audit log. |
| `POST` | `/api/v1/alerts/{alert_id}/resolve` | Supervisor / Admin | Manually resolve an alert with optional `resolution_notes`. |
| `GET` | `/api/v1/alert-rules` | Authenticated | List configured threshold rules with pagination. |
| `POST` | `/api/v1/alert-rules` | Supervisor / Admin | Create a new alert rule with validated metric, operator, and threshold bounds. |

### Deduplication Policy & Alert Episodes
1. **Deduplication Key:** `device:{device_id}:rule:{rule_id}` (or `worksite:{worksite_id}:rule:{rule_id}`).
2. **Active Episode:** If an alert already exists in `triggered` or `acknowledged` status for this key, subsequent incoming readings that satisfy the condition are deduplicated without creating duplicate active alerts.
3. **Episode Reset:** Once an alert is `resolved` or `expired`, any subsequent breach is treated as a genuinely new alert episode with a new UUID and timestamp.

### Role-Based Access Control
- **Device Credential Isolation:** Device tokens (`X-Device-Token`) are strictly rejected with HTTP 401 on user/supervisor alert endpoints to prevent device impersonation of safety supervisors.
- **Supervisor Role:** Acknowledgement and rule creation require a user entity with role `supervisor` or `admin`. Read-only `viewer` accounts receive HTTP 403 Forbidden.

#### Example Acknowledge Request
```bash
curl -X POST "http://localhost:8000/api/v1/alerts/e0a1b2c3-d4e5-4f6a-8b9c-0d1e2f3a4b5c/acknowledge" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001" \
  -d '{
    "action_taken": "Provided hydration and moved outdoor crew to ventilated break tent.",
    "notes": "Ambient heat index reached 42.5 C at Dock 4."
  }'
```

#### Example Acknowledge Response (`200 OK`)
```json
{
  "id": "e0a1b2c3-d4e5-4f6a-8b9c-0d1e2f3a4b5c",
  "status": "acknowledged",
  "acknowledged_at": "2026-10-25T10:20:00Z",
  "acknowledged_by": "00000000-0000-0000-0000-000000000001",
  "action_taken": "Provided hydration and moved outdoor crew to ventilated break tent.",
  "message": "Alert acknowledged successfully."
}
```

---

## Module 12: Human-User Authentication and Role-Based Access Control (RBAC)

Module 12 implements human-user authentication and authorization, keeping human credentials completely segregated from IoT hardware credentials.

### 1. Permission Matrix

| Capability | `admin` | `supervisor` | `viewer` | `device` (IoT Node) |
|---|:---:|:---:|:---:|:---:|
| **Ingest Sensor Telemetry** (`POST /readings`) | ❌ | ❌ | ❌ | ✅ (`X-Device-Token`) |
| **View Device Inventory** (`GET /devices`) | ✅ | ✅ | ✅ | ❌ |
| **View Latest Readings** (`GET /readings/latest`) | ✅ | ✅ | ✅ | ❌ |
| **View Historical Data** (`GET /readings/history`) | ✅ | ✅ | ✅ | ❌ |
| **View Alert Rules** (`GET /alert-rules`) | ✅ | ✅ | ✅ | ❌ |
| **Create/Edit Alert Rules** (`POST /alert-rules`) | ✅ | ✅ | ❌ | ❌ |
| **View Alerts** (`GET /alerts`) | ✅ | ✅ | ✅ | ❌ |
| **Acknowledge Alerts** (`POST /alerts/{id}/acknowledge`) | ✅ | ✅ | ❌ | ❌ |
| **Resolve Alerts** (`POST /alerts/{id}/resolve`) | ✅ | ✅ | ❌ | ❌ |
| **User Management** (`/users` CRUD) | ✅ | ❌ | ❌ | ❌ |
| **View Own Profile** (`GET /auth/me`) | ✅ | ✅ | ✅ | ❌ |

### 2. Password Hashing (Argon2id)

Passwords are never stored or logged in plaintext. They are hashed using **Argon2id** (the OWASP recommended password hashing scheme) via `argon2-cffi`:
- **Memory Cost:** 64 MiB (`65536` KiB)
- **Time Cost:** 3 iterations
- **Parallelism:** 4 threads
- **Salt Length:** 16 bytes
- **Hash Length:** 32 bytes

### 3. Session & Token Lifecycle

- **Format:** JSON Web Token (JWT) signed with HMAC-SHA256 (`HS256`).
- **Signature Secret:** Configured via `SECRET_KEY` in environment variables.
- **Claims:**
  - `sub`: User UUID string
  - `email`: User registered email address
  - `role`: Role (`admin`, `supervisor`, `viewer`)
  - `iat`: Timestamp issued (UTC)
  - `exp`: Expiration timestamp (default: 8 hours / 480 minutes)
  - `type`: `"access"`
- **Generic Login Failure:** `POST /api/v1/auth/login` returns a generic `401 Unauthorized ("Invalid email or password.")` regardless of whether the email exists or password failed, eliminating username enumeration.
- **Deactivated Accounts:** Deactivated accounts (`is_active = False`) are rejected at login and immediately denied on subsequent requests even if their token has not yet expired.

### 4. Strict Credential Separation

- IoT devices authenticate exclusively via `X-Device-Token` with per-device SHA-256 pre-shared key hashes on `POST /api/v1/readings`.
- Human endpoints (`/devices`, `/readings/latest`, `/readings/history`, `/alerts`, `/users`, etc.) explicitly reject any request providing `X-Device-Token`.
- Ingestion endpoint (`POST /api/v1/readings`) explicitly rejects human user JWT tokens and `X-User-Id` headers.
- Device credentials can **never** acknowledge alerts, change alert rules, or access human user management.

### 5. Administrator Provisioning Utility

To prevent default hardcoded administrator accounts, new administrators are provisioned via the secure CLI tool:

```bash
# Interactive password prompt (recommended for development and deployment):
PYTHONPATH=. backend/.venv/bin/python3 -m app.cli.provision_admin --email admin@heatshield.gov.in --name "National Admin" --role admin
```

### 6. Worksite Scoping Model & Limitations

- Currently, user accounts operate at the organization level (`viewer`, `supervisor`, `admin`).
- Devices, readings, and alerts contain an optional `worksite_id` foreign key.
- While endpoints allow filtering by `worksite_id`, individual supervisor user accounts are not yet isolated to a single worksite partition in the database schema. All supervisors within an organization can view and acknowledge alerts across registered worksites. Worksite-isolated tenancy is planned for future modules.

### 7. Deployment Security Requirements & Production Invariants

When `APP_ENV=production`, the application performs strict startup validation on `Settings`:
- **Debug Mode Forbidden:** `DEBUG` must be `False`.
- **Secret Key Enforcement:** `SECRET_KEY` must be at least 32 characters long and cannot match default development strings.
- **Database Engine Check:** `DATABASE_URL` must point to a PostgreSQL instance (`postgresql://` or `postgresql+psycopg2://`). In-memory SQLite is strictly rejected in production.
- **CORS Restriction:** `CORS_ORIGINS` cannot contain the wildcard `*`. Explicit origins (e.g. `https://heatshield.example.com`) are mandatory.
- **HTTPS Mandatory:** JWT tokens and passwords must only be transmitted over TLS 1.3 / HTTPS in deployed environments.
- **Rate Limiting:** Upstream rate limiting (e.g. via Nginx, Cloudflare, or reverse proxy) on `POST /api/v1/auth/login` is required to mitigate brute-force attempts.

---

## Container Deployment (Docker / Podman)

The backend provides a production-grade multi-stage container image using `python:3.12-slim-bookworm` running as a non-privileged user (`heatshield` UID 10001):

### Build Backend Image
```bash
# Using Podman or Docker
podman build -t heatshield-backend:latest -f Dockerfile .
```

### Run Backend Container
```bash
podman run -d --name heatshield_api \
  -p 8000:8000 \
  -e APP_ENV=production \
  -e SECRET_KEY="a-secure-random-32-byte-hex-string-for-prod" \
  -e DATABASE_URL="postgresql://heatshield_prod:password@postgres_host:5432/heatshield_prod" \
  -e CORS_ORIGINS="https://app.heatshield.local" \
  heatshield-backend:latest
```

The container entrypoint (`scripts/start.sh`) automatically runs `alembic upgrade head` before launching Uvicorn multi-worker processes if `RUN_MIGRATIONS_ON_STARTUP=true` (default: false to ensure explicit database migration control).

---

## Health & Database Readiness Probes

| Endpoint | Purpose | Semantics |
|---|---|---|
| `GET /health` | **Liveness** | Always reports 200 OK (`status="healthy"`) as long as API process runs, regardless of database status. |
| `GET /ready` | **Readiness** | Live connectivity check (`SELECT 1`). Returns `200 OK` (`services.database="connected"`) if healthy; `503 Service Unavailable` (`services.database="unavailable"`) if database is down; or `services.database="not_configured"` if `DATABASE_URL` is unset. |

---

## Running Automated Tests

Run the full test suite with `pytest`:

```bash
PYTHONPATH=. pytest -v
```

### Test Suite Structure

1. **Unit & Service Tests (isolated in-memory database):**
   - `tests/test_deployment_config.py`: (Module 14) Startup configuration validation, production invariant rejection tests (weak secret key, debug mode, SQLite rejection in prod, wildcard CORS rejection).
   - `tests/test_end_to_end_integration.py`: (Module 13) Complete multi-hop data flow from IoT ingestion, deduplication, alert episode triggering, viewer historical query, to supervisor acknowledgement/resolution and credential separation.
   - `tests/test_resilience_and_failures.py`: (Module 13) Robustness and failure mode tests: unauthorized devices, conflicting payload duplicates, non-finite inputs, clock skew, out-of-domain readings, inverted history windows, deactivated user tokens, and simulated database failures.
   - `tests/test_auth_and_rbac.py`: (Module 12) Argon2id password hashing, JWT bearer generation, role authorization matrix, and user lifecycle CRUD.
   - `tests/test_alert_engine.py`: (Module 8) Alert rule validation, deterministic evaluation, deduplication, lifecycle transitions, supervisor authorization.
   - `tests/test_readings_history.py`: (Module 11) Historical telemetry filtering, descriptive statistics (min/max/mean), gap detection, and alert history.
   - `tests/test_heat_index.py`: (Module 7) NOAA Rothfusz & Steadman polynomial calculations, domain bounds, quality and staleness handling.
   - `tests/test_readings_ingestion.py`: (Module 6) Authenticated telemetry ingestion, token verification, quality classification, idempotency.
   - `tests/test_app.py`: Factory, router, CORS, centralized errors.
   - `tests/test_health.py`: Liveness and readiness contracts.
   - `tests/test_models.py`: Model instantiation, checks, and password hash masking.
   - `tests/test_db_readiness.py`: Readiness probe with mocked database states.
   - `tests/test_repositories.py`: Repository operations and query ordering (using isolated memory session).

2. **PostgreSQL Integration Tests:**
   - `tests/test_postgres_integration.py`: Runs real PostgreSQL tests verifying foreign-key `RESTRICT` enforcement, unique constraint deduplication with transaction rollback, check constraints, JSONB parameters, and timezone queries.
   - To target a specific test database, set `POSTGRES_TEST_URL`:
     ```bash
     POSTGRES_TEST_URL="postgresql://user:pass@host:port/testdb" PYTHONPATH=. pytest tests/test_postgres_integration.py -v
     ```
   - If PostgreSQL is not accessible, integration tests automatically skip with a clear message while all unit tests pass.

---

## Troubleshooting Common Connection Failures

1. **`ModuleNotFoundError: No module named 'psycopg'`**:
   - The default `postgresql://` URL in SQLAlchemy 2.0+ looks for `psycopg` (v3). Our backend automatically maps `postgresql://` to `postgresql+psycopg2://` so `psycopg2-binary` works seamlessly.
2. **Connection Refused (`Is the server running on host "localhost"...`):**
   - Ensure your PostgreSQL service or container is running and listening on the expected port (`5432`).
3. **Authentication Failed (`FATAL: password authentication failed`):**
   - Verify the username and password in `.env` match your local PostgreSQL configuration.
4. **Database does not exist:**
   - Create the target database using `CREATE DATABASE <name>;` before applying migrations.
