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
