# HeatShield Bharat — Database Schema Notes

> **Status:** Implementation complete (Module 4). All 8 SQLAlchemy models,
> Alembic migrations (`0001_initial_schema.py`), and repository abstractions
> are implemented and verified.

## Detailed Design & Architecture

The full logical database design — including entity specifications, column
definitions, constraints, indexes, and ER diagram — is documented in:

📄 **[docs/architecture/database-design.md](../docs/architecture/database-design.md)**

## Implemented Database Stack

- **Engine:** PostgreSQL 15+
- **Driver:** `psycopg2-binary`
- **ORM:** SQLAlchemy 2.0 (`backend/app/models/`)
- **Migrations:** Alembic (`backend/migrations/`)
- **Persistence Layer:** Repositories (`backend/app/repositories/`)

## Implemented Entities (8)

| Table | Model Class | Repository | Purpose |
|---|---|---|---|
| `worksites` | `Worksite` | `app.repositories.worksite` | Monitored physical sites |
| `devices` | `Device` | `app.repositories.device` | Registered ESP32 sensor nodes |
| `sensor_readings` | `SensorReading` | `app.repositories.reading` | Time-series environmental measurements |
| `alert_rules` | `AlertRule` | `app.repositories.alert` | Configurable alert conditions with versioning |
| `alerts` | `Alert` | `app.repositories.alert` | Generated alert events with lifecycle tracking |
| `alert_acknowledgements` | `AlertAcknowledgement` | `app.repositories.alert` | Acknowledgement records with safety actions |
| `users` | `User` | — | Dashboard user accounts (auth deferred) |
| `audit_logs` | `AuditLog` | — | Security and administrative action records |

## Key Design Decisions

- **Timestamps:** UTC via `TIMESTAMPTZ` ([ADR-009](../docs/decisions/architecture-decisions.md)).
- **Data quality:** `quality_status` enum per reading ([ADR-010](../docs/decisions/architecture-decisions.md)).
- **Deduplication:** `UNIQUE (device_id, event_id)` with transactional rollback ([ADR-011](../docs/decisions/architecture-decisions.md)).
- **Alert lifecycle:** Independent severity (`info` to `emergency`) and status (`triggered` to `resolved`) ([ADR-012](../docs/decisions/architecture-decisions.md)).
- **Soft deletion:** `is_active` flags, `RESTRICT` foreign keys on deletion ([ADR-013](../docs/decisions/architecture-decisions.md)).
- **Heat-risk:** Formula deferred to Module 6+ ([ADR-014](../docs/decisions/architecture-decisions.md)).
- **Simulated data:** `source_mode` field distinguishes `hardware` from `simulated`.
- **Database Readiness:** Real ping check integrated into `GET /ready` probe ([ADR-017](../docs/decisions/architecture-decisions.md)).

## Migration Commands

From the `backend/` directory:

```bash
# View migration history
alembic history

# Show current database revision
alembic current

# Apply all migrations
alembic upgrade head

# Rollback one revision (caution: drops tables/data in that revision)
alembic downgrade -1
```
