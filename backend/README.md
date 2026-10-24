# HeatShield Bharat — Backend Service

The backend service for **HeatShield Bharat**, an IoT-based environmental heat-monitoring and early-warning system.

> **Current Status (Module 4):** Foundational FastAPI application, environment configuration, PostgreSQL database layer (SQLAlchemy 2.0 ORM models, Alembic migrations, persistence repositories), health and database readiness probes, and automated test suite.
>
> **Important Note on Limitations:** Telemetry ingestion endpoints (`POST /api/v1/readings`), heat-risk calculation algorithms, and alert dispatch are **not yet implemented** (scheduled for subsequent modules).

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
│   │       └── router.py     # Versioned router aggregation (/api/v1)
│   ├── core/
│   │   ├── __init__.py
│   │   └── exceptions.py     # Custom exceptions and centralized error handlers
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
│   └── schemas/
│       ├── __init__.py       # Schema exports
│       ├── common.py         # ErrorResponse and ErrorDetail schemas
│       └── health.py         # HealthResponse and ReadyResponse schemas
├── tests/
│   ├── conftest.py           # Test fixtures and isolated configuration
│   ├── test_app.py           # Tests for factory, routing, CORS, errors, and settings
│   ├── test_db_readiness.py  # Tests for database readiness probe (connected, unavailable, etc.)
│   ├── test_health.py        # Tests for /health and /ready endpoints
│   ├── test_models.py        # Unit tests for ORM models and constraints
│   ├── test_postgres_integration.py # Real PostgreSQL 15 integration tests
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
  "input_relative_humidity_pct": 65.0,
  "informational_screening_level": "extreme_danger",
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
- **`invalid_input`**: Non-finite float (NaN/Inf) or humidity outside [0, 100].
- **`invalid_quality`**: Upstream reading carries an `invalid` quality classification.
- **`suspect_quality`**: Evaluated normally, but flags `status: "suspect_quality"` with an audit note.

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

1. **Unit Tests (no database required):**
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
