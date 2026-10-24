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
├── firmware/          # ESP32 firmware (pending hardware confirmation)
│   ├── README.md
│   └── tests/
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
| Module 5 — ESP32 Firmware & Sensor Integration | 🔲 Not started (hardware unconfirmed) |
| Module 6 — Frontend Dashboard | 🔲 Not started |
| Module 7 — Heat-Risk Engine & Calculation | 🔲 Not started |
| Module 8 — Alerts & Notifications | 🔲 Not started |
| Module 9 — Integration & End-to-End Testing | 🔲 Not started |
| Module 10+ — Deployment & Production Hardening | 🔲 Not started |

### Implemented features

- Repository structure and documentation foundation.
- Development conventions (`.editorconfig`, `.gitignore`).
- Architecture and decision records.
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
- Alembic database migration environment and verified initial migration (`0001_initial_schema.py`).
- Persistence layer repositories for worksites, devices, sensor readings, and alert management.
- Live database connectivity check integrated into `/ready` probe (reporting `connected`, `unavailable` [503], or `not_configured`).
- Automated test suite (35 unit and real PostgreSQL 15 integration tests with pytest).

### Planned features (not yet implemented)

- ESP32 firmware and physical sensor integration (Module 5).
- Frontend React dashboard (Module 6).
- Heat-index / WBGT / Humidex calculation engine (Module 7).
- Sensor data ingestion and telemetry API (`POST /api/v1/readings`).
- Alert notification delivery (SMS, email, webhooks).
- User and device authentication implementation.

---

## Documentation

- [Backend Documentation](backend/README.md)
- [Architecture Overview](docs/architecture/overview.md)
- [System Architecture](docs/architecture/system-architecture.md)
- [Data Flow Specification](docs/architecture/data-flow.md)
- [Database Design](docs/architecture/database-design.md)
- [API Contracts](docs/architecture/api-contracts.md)
- [Architecture Decisions](docs/decisions/architecture-decisions.md)
- [Sensor Reading JSON Schema](docs/contracts/sensor-reading.schema.json)
- [Firmware Plans](firmware/README.md)
- [Database Schema Notes](database/schema-notes.md)

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).
