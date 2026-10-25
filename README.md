# HeatShield Bharat

**IoT-based environmental heat-monitoring and early-warning system for India.**

HeatShield Bharat is a final-year engineering major project that combines physical
sensors, embedded firmware, a cloud backend, and a web dashboard to monitor
environmental heat conditions in real time, calculate heat-risk indices, and
deliver timely alerts.

---

## Project Objectives

1. Collect real environmental sensor data (temperature, humidity, and related
   parameters) using ESP32-based IoT nodes.
2. Transmit telemetry securely to a cloud backend via authenticated REST APIs.
3. Store, process, and analyse historical readings in a PostgreSQL database.
4. Calculate documented heat-risk indices and trigger configurable alerts.
5. Present live and historical data on a responsive web dashboard.
6. Support offline firmware operation with local alerting and data buffering.

---

## Planned Technology Stack

| Layer | Technology |
|---|---|
| Hardware | ESP32 microcontroller + environmental sensors *(unconfirmed — see below)* |
| Firmware | Arduino framework for ESP32 *(pending hardware confirmation)* |
| Backend | Python · FastAPI |
| Database | PostgreSQL · SQLAlchemy ORM · Alembic migrations |
| Frontend | React · TypeScript · Vite |
| Testing | pytest (backend) · Vitest (frontend, planned) |
| Dev tools | Git · Google Antigravity coding agent |

---

## High-Level Architecture

```
┌──────────────┐       HTTPS/JSON        ┌──────────────┐
│  ESP32 Node  │ ─────────────────────►  │   FastAPI     │
│  (sensors)   │   authenticated API     │   Backend     │
└──────────────┘                         └──────┬───────┘
       │ local alerts                           │
       ▼                                        ▼
  buzzer / LED                            PostgreSQL DB
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │    React      │
                                         │   Dashboard   │
                                         └──────────────┘
```

See [docs/architecture/overview.md](docs/architecture/overview.md) for details.

---

## Repository Structure

```
heatshield-bharat/
├── firmware/          # ESP32 firmware scaffolding (HAL, validation, alert logic)
│   ├── README.md
│   ├── heatshield/    # Arduino sketch & hardware-independent headers
│   │   ├── heatshield.ino
│   │   ├── reading_types.h
│   │   ├── sensor_interface.h
│   │   ├── validation.h
│   │   ├── alert_logic.h
│   │   └── telemetry_boundary.h
│   └── tests/         # Host-runnable C++ and contract test suites
├── backend/           # FastAPI application
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/          # React + TypeScript + Vite dashboard
│   ├── src/           (created when scaffolded)
│   ├── public/        (created when scaffolded)
│   └── .env.example
├── database/          # Schema notes and migration plans
│   └── schema-notes.md
├── docs/              # Project documentation
│   ├── architecture/
│   ├── decisions/
│   ├── hardware/
│   ├── testing/
│   └── reports/
├── scripts/           # Development and utility scripts
├── .editorconfig
├── .env.example
├── .gitignore
└── README.md          ← you are here
```

---

## Hardware Confirmation Status

> **⚠ Hardware is UNCONFIRMED.**
>
> The exact ESP32 board model, sensor modules, and supporting components have
> not yet been purchased or verified. No board-specific firmware or sensor
> drivers have been implemented.
>
> See [firmware/README.md](firmware/README.md) for the information that must
> be confirmed before firmware development begins.

---

## Prerequisites

| Tool | Minimum Version | Notes |
|---|---|---|
| Git | 2.x | Version control |
| Python | 3.11+ | Backend development |
| pip | latest | Python package management |
| Node.js | 18+ | Frontend tooling |
| npm | 9+ | Frontend package management |
| PostgreSQL | 15+ | Database *(install when needed)* |

### Detected on this machine

- Git 2.56.0 ✅
- Python 3.14.8 ✅
- pip 26.0.1 ✅
- Node.js 20.18.0 ✅
- npm 10.8.2 ✅
- PostgreSQL — **not yet installed** (not required for Module 1)

---

## Development Setup Overview

### 1. Clone the repository

```bash
git clone <repository-url>
cd heatshield-bharat
```

### 2. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit with your local settings if needed

# Run automated tests
PYTHONPATH=. pytest -v

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

See [backend/README.md](backend/README.md) for full backend documentation.

### 3. Frontend setup (when scaffolded)

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

### 4. Database setup

1. Install and start PostgreSQL 15+ (or run a container via `podman`/`docker`).
2. Create a development database (e.g. `heatshield_dev`).
3. Set `DATABASE_URL` in `backend/.env`.
4. Apply the baseline migrations from `backend/`:

```bash
cd backend
alembic upgrade head
```

See [database/schema-notes.md](database/schema-notes.md) and [backend/README.md](backend/README.md) for details.

### 5. Firmware setup (when hardware is confirmed)

See [firmware/README.md](firmware/README.md).

---

## Current Development Status

| Module | Status |
|---|---|
| **Module 1 — Project Foundation** | ✅ Complete |
| **Module 2 — Architecture & Data Contracts** | ✅ Complete |
| **Module 3 — FastAPI Backend Foundation** | ✅ Complete |
| **Module 4 — PostgreSQL Integration & Persistence** | ✅ Complete |
| **Module 5 — ESP32 Firmware Scaffolding & Sensor HAL** | ✅ Complete *(Scaffolding & HAL; Hardware UNCONFIRMED)* |
| **Module 6 — Telemetry Ingestion & Reliability** | ✅ Complete |
| **Module 7 — Heat-Risk Engine & Calculation** | ✅ Complete |
| **Module 8 — Alert Rules and Alert Lifecycle** | ✅ Complete |
| **Module 9 — React Frontend Foundation** | ✅ Complete |
| **Module 10 — Live Monitoring Dashboard and Device Status** | ✅ Complete |
| **Module 11 — Historical Data, Charts and Analytics** | ✅ Complete |
| **Module 12 — Authentication and Role-Based Access Control** | ✅ Complete |
| **Module 13 — End-to-End Integration and Automated Testing** | ✅ Complete |
| **Module 14 — Deployment and Operational Readiness** | ✅ Complete |
| Module 15+ — Field Validation, Physical Calibration & Packaging | 🔲 Blocked (Pending Hardware) |

### Implemented features

- Repository structure and documentation foundation.
- Development conventions (`.editorconfig`, `.gitignore`).
- Architecture and decision records (ADR-001 through ADR-025).
- Detailed system architecture and data-flow documentation.
- Logical database design (8 entities, ER diagram, constraints, indexes).
- API data contracts (9 endpoints, request/response schemas).
- JSON Schema for sensor-reading payload.
- Heat-risk data contract and separation of concerns.
- Foundational FastAPI application with application factory pattern (`create_app`).
- Environment-driven configuration management via Pydantic Settings.
- Liveness (`/health`) and live readiness (`/ready`) endpoints adhering to contracts.
- Centralized error handling without information disclosure.
- SQLAlchemy 2.0 ORM models for all 8 entities (`worksites`, `devices`, `sensor_readings`, `alert_rules`, `alerts`, `alert_acknowledgements`, `users`, `audit_logs`).
- Alembic database migration environment (`0001_initial_schema.py` and `0002_add_device_api_key_hash.py`).
- Persistence layer repositories for worksites, devices, sensor readings, and alert management.
- Live database connectivity check integrated into `/ready` probe (reporting `connected`, `unavailable` [503], or `not_configured`).
- ESP32 Arduino firmware scaffolding with Hardware Abstraction Layer (`ISensor`, `UnconfiguredSensor`, `DiagnosticSimulatedSensor`).
- Strongly typed environmental reading data contract (`reading_types.h`) matching backend API JSON schema with explicit presence flags (no silent zero substitution).
- Numerical sanity and physical plausibility validation engine (`validation.h`) with NaN/Inf detection.
- Autonomous, offline-capable local alert evaluation (`alert_logic.h`) with fail-safe unknown state (missing/corrupted data never evaluates to green safe).
- Stateful thermal hysteresis deadband preventing rapid threshold bouncing.
- Decoupled actuator (`IAlertOutput`) and telemetry boundary (`ITelemetryPublisher`) with zero hardcoded credentials.
- Telemetry Ingestion API (`POST /api/v1/readings`) with Pydantic request validation and strict schema enforcement.
- Per-device authentication via SHA-256 pre-shared key hashes with constant-time verification and generic 401 error envelopes.
- Idempotent deduplication via database constraint `uq_readings_device_event` returning 200 OK (`deduplicated: true`) on identical retries.
- Duplicate payload conflict detection returning 409 Conflict when event IDs are reused with differing measurements.
- Telemetry quality classification engine (`valid`, `suspect`, `invalid`, `missing`) with timestamp drift reconciliation.
- Explainable Heat-Risk Calculation Engine (`app/services/heat_index.py`) implementing the authoritative NWS Rothfusz (1990) equation and Steadman (1979) physiological apparent temperature model.
- Transparent calculation endpoint (`POST /api/v1/readings/calculate-heat-index`) with formula versioning, equation-branch tracking, domain safety limits (20°C to 55°C), and explicit scientific limitations (distinguishing Heat Index from WBGT).
- Alert Rules engine supporting configurable environmental thresholds (`temperature_c`, `relative_humidity_pct`, `heat_index_c`) with numerical bounds and operator validation (`gt`, `gte`, `lt`, `lte`, `eq`).
- Deterministic alert evaluation service (`app/services/alert_engine.py`) integrating Module 7 Heat Index calculations with fail-safe handling (missing/stale data never assumed safe).
- Episode deduplication policy (`device:{device_id}:rule:{rule_id}`) preventing duplicate active alert creation during ongoing sustained heat incidents.
- Supervisor acknowledgement and resolution lifecycle (`triggered` -> `acknowledged` -> `resolved`, plus `expired`) with audit trail logging in `alert_acknowledgements`.
- Role-based authorization (`app/core/user_auth.py`) strictly isolating device tokens (`X-Device-Token`) from supervisor management endpoints (`/api/v1/alerts`, `/api/v1/alert-rules`).
- React 19 + TypeScript + Vite frontend foundation with client-side routing (React Router v7), responsive layout, and custom industrial safety Vanilla CSS design system.
- Accessible UI states: `LoadingState` (role="status"), `ErrorState` (role="alert"), `EmptyState`, and `StatusBadge` (combining icons, text labels, and color).
- Type-safe API client (`services/api.ts`) with timeout handling, network failure recovery, JSON safety, and environment-driven base URL (`VITE_API_BASE_URL`).
- Live backend readiness probe integrating `GET /ready` and `GET /health` into the navigation header and Overview page.
- Real API integration for Module 8 alerts (`GET /api/v1/alerts`, `GET /api/v1/alert-rules`) and interactive testbench for Module 7 Heat-Risk calculations (`POST /api/v1/readings/calculate-heat-index`).
- Module 10 Live Monitoring Dashboard (`/`) displaying real-time environmental metrics (temperature in °C, humidity in %, quality status, measured/server timestamps), Module 7 NWS heat index screening, Module 8 active alert summary, and registered device inventory.
- Bounded polling refresh engine with configurable intervals (10s, 15s default, 30s, 60s, paused), overlap prevention, unmount timer cleanup, and cached-stale banner on network failure.
- Module 11 Historical Data API (`GET /api/v1/readings/history`) with bounded date-range validation (max 30 days), deterministic ordering, SQL-level min/max/mean metrics, and alert-history filtering by time window (`GET /api/v1/alerts?start_time=...&end_time=...`).
- Module 11 Historical Analytics & Charts (`/analytics`): pure SVG time-series charts (temperature in °C, humidity in %, and NOAA Rothfusz heat index in °C) with gap detection (breaks lines on missing readings or gaps > 45 minutes; never plots zero for missing measurements), summary cards, and paginated telemetry table.
- **Module 12 Human Authentication & RBAC**:
  - Secure password hashing using Argon2id with OWASP recommended cost parameters.
  - JWT Bearer access token generation with configurable expiration window (`AUTH_TOKEN_EXPIRE_MINUTES`) and HMAC-SHA256 signature verification.
  - Role hierarchy with server-side enforcement: `admin` (user management, configuration), `supervisor` (alert acknowledgement, resolution, rule management), and `viewer` (read-only monitoring access).
  - Strict two-way credential isolation: IoT device tokens (`X-Device-Token`) are rejected on human endpoints, and user tokens are rejected on device ingestion (`POST /api/v1/readings`).
  - Administrative user provisioning script (`app.cli.provision_admin`) preventing default hardcoded credentials.
  - User lifecycle endpoints (`POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`, `GET /api/v1/users`, `POST /api/v1/users`, `PATCH /api/v1/users/{id}`) with self-lockout prevention.
  - Frontend authentication: Sign In page (`/login`), `AuthContext`, session-scoped token storage (`sessionStorage`), automatic Bearer header injection, 401 session expiry handling, route protection (`ProtectedRoute`), and role-aware UI controls in `AlertsPage` and `Header`.
- **Module 13 End-to-End Integration & Testing**:
  - Master test execution script (`scripts/run_all_tests.sh`) executing firmware contracts, host C++ HAL tests, backend pytest suites, frontend TypeScript/lint checks, Vitest suites, and production build verification.
  - End-to-end integration test suite (`backend/tests/test_end_to_end_integration.py`) verifying full data lifecycle: validated ingestion -> deduplication -> PostgreSQL persistence -> heat-risk calculation -> alert triggering -> supervisor ack/resolve audit trail -> viewer query -> two-way credential segregation.
  - Resilience and failure test suite (`backend/tests/test_resilience_and_failures.py`) covering 16 error scenarios: unauthorized devices, conflicting duplicate payloads, non-finite inputs, clock skew, out-of-domain temperatures, inverted query windows, deactivated user tokens, and simulated DB connection failures.
  - Frontend end-to-end integration tests (`frontend/src/test/IntegrationE2E.test.tsx`) verifying route redirects, telemetry units (°C and %), missing value handling ("Unavailable" without converting to zero), stale data warnings, and role-based alert controls.
  - GitHub Actions CI workflow (`.github/workflows/ci.yml`) with automated PostgreSQL 15 test service container.
  - Integration test documentation report ([docs/testing/integration-test-report.md](docs/testing/integration-test-report.md)).
- **Module 14 Deployment and Operational Readiness**:
  - Reproducible multi-service container orchestration using Docker Compose (`docker-compose.yml`) coordinating PostgreSQL 15 with persistent storage volume (`heatshield_pgdata`), FastAPI ASGI application, and Nginx reverse proxy.
  - Multi-stage Docker build for backend (`backend/Dockerfile`) with Python 3.12-slim-bookworm, non-root user execution (`heatshield` UID 10001), automated dependency installation, explicit migration runner (`backend/scripts/start.sh`), and healthcheck probes.
  - Multi-stage Docker build for frontend (`frontend/Dockerfile`) with Node 22 build environment, Alpine Nginx runtime, SPA HTML5 routing fallback (`try_files $uri $uri/ /index.html`), API reverse proxy (`/api/` -> `http://backend:8000/api/`), gzip compression, and HTTP security headers.
  - Strict production settings validation (`backend/app/config.py`): in production (`APP_ENV=production`), enforces `DEBUG=False`, non-default `SECRET_KEY` >= 32 characters, PostgreSQL database URI (rejects SQLite), and forbids wildcard `*` CORS origins without crashing or printing secret values.
  - Explicit database migration discipline (`alembic upgrade head`) preserving existing data, with documented backup/restore procedures (`pg_dump` / `pg_restore`).
  - Operational runbook (`docs/deployment/runbook.md`) documenting topology, environment variable references, provisioning, migration, rollback, backup, secret rotation, and troubleshooting procedures.
  - Comprehensive deployment test suite (`backend/tests/test_deployment_config.py`) verifying dev defaults, test mode, and production security validation invariants.
- Honest hardware state representation: physical ESP32 boards unconfirmed, missing readings displayed as "Unavailable" without assuming zero, and stale data explicitly tagged.
- Comprehensive automated test suites: 47 frontend Vitest tests (100% pass) and 178 backend/firmware tests (225 total passing automated software tests; 148 backend unit tests + 21 firmware contract/HAL tests + 8 skipped real-PostgreSQL integration tests).

### Testing & Verification

To run all automated test suites across all project layers in one command:
```bash
./scripts/run_all_tests.sh
```

### Planned features (not yet implemented)

- Physical hardware procurement and driver integration (Module 5 Phase 2).

---

## Documentation

- [Deployment & Operational Runbook](docs/deployment/runbook.md)
- [End-to-End Testing & Integration Report](docs/testing/integration-test-report.md)
- [Frontend Documentation](frontend/README.md)
- [Backend Documentation](backend/README.md)
- [Firmware Documentation & Scaffolding](firmware/README.md)
- [Hardware Selection & Physical Integration Guide](docs/hardware/hardware-selection.md)
- [Heat-Risk Calculation Method & Explainability](docs/architecture/heat-risk-method.md)
- [Alert Lifecycle & Deduplication Specification](docs/architecture/alert-lifecycle.md)
- [Architecture Overview](docs/architecture/overview.md)
- [System Architecture](docs/architecture/system-architecture.md)
- [Data Flow Specification](docs/architecture/data-flow.md)
- [Database Design](docs/architecture/database-design.md)
- [API Contracts](docs/architecture/api-contracts.md)
- [Architecture Decisions](docs/decisions/architecture-decisions.md)
- [Sensor Reading JSON Schema](docs/contracts/sensor-reading.schema.json)
- [Database Schema Notes](database/schema-notes.md)

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).
