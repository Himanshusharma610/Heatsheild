# HeatShield Bharat — Architecture Decision Records

> Decisions are numbered chronologically. Each decision can be **accepted**,
> **superseded**, or **amended** as the project evolves. When amending a
> decision, add a new entry and reference the original.

---

## ADR-001: FastAPI for the Backend

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** We need a Python web framework for the REST API. The backend
  will handle telemetry ingestion, data queries, and alert processing.
- **Decision:** Use FastAPI.
- **Rationale:**
  - Async support for handling concurrent telemetry from multiple devices.
  - Automatic OpenAPI documentation for API exploration and testing.
  - Pydantic-based request/response validation.
  - Strong ecosystem and community support.
  - Team familiarity with Python.
- **Consequences:** Requires Python 3.11+. Async patterns may add complexity
  but improve throughput for I/O-bound operations.

---

## ADR-002: PostgreSQL for Persistence

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** The system must store time-series sensor readings, device
  metadata, alert rules, and alert history reliably.
- **Decision:** Use PostgreSQL as the primary database.
- **Rationale:**
  - Robust, battle-tested relational database.
  - Excellent support for time-series queries and indexing.
  - Extensions available (e.g., TimescaleDB) if scaling is needed.
  - Strong integration with SQLAlchemy and Alembic.
  - Free and open-source.
- **Consequences:** Requires PostgreSQL installation on development and
  deployment machines. Team must learn basic PostgreSQL administration.

---

## ADR-003: SQLAlchemy ORM and Alembic Migrations

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** We need a way to define the database schema in Python and
  manage schema changes over time.
- **Decision:** Use SQLAlchemy as the ORM and Alembic for migrations.
- **Rationale:**
  - Industry-standard Python ORM with both Core and ORM interfaces.
  - Alembic provides version-controlled, repeatable migrations.
  - Tight integration with FastAPI via dependency injection.
- **Consequences:** Schema changes must go through Alembic migrations.
  Raw SQL should be avoided in application code except for performance-
  critical queries.

---

## ADR-004: React with TypeScript and Vite for the Frontend

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** The dashboard needs to display live data, historical charts,
  alerts, and device management views.
- **Decision:** Use React with TypeScript, built with Vite.
- **Rationale:**
  - React is widely adopted with extensive component ecosystem.
  - TypeScript adds compile-time type safety and better IDE support.
  - Vite provides fast development server and optimised production builds.
  - Team has some React experience.
- **Consequences:** Frontend developers need TypeScript knowledge. Bundle
  size must be monitored for production.

---

## ADR-005: Versioned REST/JSON API

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** The ESP32 firmware, React dashboard, and potential third-party
  consumers need a stable interface to the backend.
- **Decision:** Expose a versioned REST API with JSON payloads, prefixed
  with `/api/v1/`.
- **Rationale:**
  - REST is simple and well-understood by all team members.
  - JSON is lightweight and natively supported by both ESP32 (ArduinoJson)
    and React (fetch/axios).
  - Version prefix allows non-breaking API evolution.
  - FastAPI generates OpenAPI documentation automatically.
- **Consequences:** Breaking API changes require a new version prefix.
  WebSocket support may be added later for real-time dashboard updates.

---

## ADR-006: Monorepo with Separate Directories

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** The project spans firmware, backend, frontend, and documentation.
- **Decision:** Use a single Git repository with separate top-level
  directories: `firmware/`, `backend/`, `frontend/`, `database/`, `docs/`,
  and `scripts/`.
- **Rationale:**
  - Simplifies cross-cutting changes and documentation.
  - Single source of truth for the entire project.
  - Appropriate for a final-year project team size.
  - Each directory can have its own build tools and dependency management.
- **Consequences:** CI/CD pipelines must be configured per directory.
  Large binary firmware assets should be managed carefully to avoid
  bloating the repository.

---

## ADR-007: Real Sensor Data as Production Data Source

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** The system is designed to monitor real environmental conditions.
- **Decision:** The production data source is real sensor readings from
  physical ESP32 nodes.
- **Rationale:**
  - The project's value depends on real-world environmental monitoring.
  - Simulated data is useful for development and testing but must never
    be confused with real measurements.
- **Consequences:** Simulated data must be explicitly labelled (e.g., a
  `is_simulated` boolean flag or `source` column in the database).
  Development seed scripts must clearly mark their output as simulated.

---

## ADR-008: Hardware Decisions Pending

- **Status:** Pending
- **Date:** 2026-10-24
- **Context:** The exact ESP32 board, sensor models, and supporting
  components have not yet been purchased or confirmed.
- **Decision:** Defer all hardware-specific decisions (board selection,
  sensor driver, GPIO mapping, power design, offline storage method)
  until the actual components are in hand.
- **Rationale:**
  - Implementing firmware for unconfirmed hardware risks wasted effort
    and incorrect assumptions.
  - The software architecture (backend, frontend, API) can proceed
    independently of hardware details.
- **Consequences:** Firmware development cannot begin until hardware is
  confirmed. The `firmware/` directory contains only documentation.
  This decision will be superseded by a hardware-specific ADR once
  components are confirmed.

---

## ADR-009: UTC Timestamps with TIMESTAMPTZ

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** The system involves devices in the field, a backend server, and
  browser-based dashboards — potentially in different time zones. Timestamp
  consistency is critical for correct data ordering, alert evaluation, and
  historical queries.
- **Decision:** Store all timestamps in UTC using PostgreSQL `TIMESTAMP WITH
  TIME ZONE` (`TIMESTAMPTZ`). Application code passes timezone-aware datetime
  objects. API responses use ISO 8601 with `Z` suffix. The frontend converts
  to local display time.
- **Rationale:**
  - Eliminates ambiguity from DST transitions and multi-timezone deployments.
  - PostgreSQL `TIMESTAMPTZ` stores UTC internally regardless of session timezone.
  - ISO 8601 is the standard interchange format for REST APIs.
- **Consequences:** All backend code must use timezone-aware datetime objects.
  The `measured_at` field from devices is accepted as UTC (nullable if device
  clock is unreliable). The `received_at` field is always set by the server.

---

## ADR-010: Data Quality Tracking for Sensor Readings

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** Sensors can produce missing, implausible, or erroneous values.
  The system must distinguish between valid, suspect, and invalid readings
  without silently discarding data.
- **Decision:** Each sensor reading carries a `quality_status` field with values
  `valid`, `suspect`, `invalid`, or `missing`. All readings are persisted
  regardless of quality. Only `valid` readings are evaluated by the alert engine.
- **Rationale:**
  - Invalid readings are valuable for diagnostics (sensor failure detection).
  - Silent data loss makes debugging impossible.
  - Quality boundaries are broad plausibility checks, not medical or
    sensor-specification thresholds.
- **Consequences:** The alert engine must filter on `quality_status = 'valid'`.
  Dashboard views should indicate data quality visually. Quality assessment
  logic is centralised in the backend ingestion service.

---

## ADR-011: Event-Based Deduplication for Idempotent Ingestion

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** The ESP32 firmware may retry failed telemetry uploads, and
  offline-buffered readings are uploaded after reconnection. The backend must
  handle duplicate submissions without creating duplicate records.
- **Decision:** Each reading has a device-assigned `event_id` that is unique
  per device. The database enforces a `UNIQUE (device_id, event_id)` constraint.
  Duplicate submissions return `200 OK` with the existing record (idempotent).
- **Rationale:**
  - Device-side event IDs are monotonically increasing and survive reboots
    (stored in flash or derived from a counter).
  - Database-enforced uniqueness is the most reliable deduplication mechanism.
  - Idempotent responses simplify firmware retry logic.
- **Consequences:** The firmware must assign unique, stable event IDs. The
  backend ingestion handler must catch unique-constraint violations and return
  the existing record instead of an error.

---

## ADR-012: Alert Lifecycle with Status and Severity Separation

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** Alerts must track both how serious a condition is (severity) and
  where the alert is in its processing lifecycle (status). Conflating these
  dimensions causes confusion.
- **Decision:** Alerts have independent `severity` (info, warning, critical,
  emergency) and `status` (triggered, acknowledged, resolved, expired) fields.
  Alert rules are versioned with a `rule_version` integer, and alerts snapshot
  the rule version at creation time.
- **Rationale:**
  - A `critical` alert can be `acknowledged` while a `warning` alert is still
    `triggered` — these are orthogonal concepts.
  - Rule versioning enables post-hoc auditing of which rule configuration
    produced a given alert.
  - Explicit state transitions prevent invalid status changes.
- **Consequences:** The backend must enforce valid status transitions. The
  dashboard must display both severity and status. Severity levels are
  operational categories, not medical diagnoses.

---

## ADR-013: Soft Deletion for Historical Data Preservation

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** Devices and worksites may be retired, but their historical sensor
  readings, alerts, and audit records must be preserved for analysis and
  accountability.
- **Decision:** Use `is_active` boolean flags for soft deletion on worksites,
  devices, and users. Foreign keys use `RESTRICT` on delete to prevent
  accidental data loss. Hard deletion is reserved for compliance scenarios.
- **Rationale:**
  - Historical sensor data is the primary value of the system.
  - Cascade deletion of thousands of readings due to an accidental device
    delete would be catastrophic and unrecoverable.
  - Soft deletion is simple to implement and query.
- **Consequences:** All list queries must filter by `is_active` by default.
  Deactivated entities can be queried explicitly when needed. Storage grows
  over time; a retention policy may be needed later.

---

## ADR-014: Heat-Risk Formula Selection Deferred

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** The system will calculate heat-stress indicators from sensor
  readings. Multiple formulas exist (Steadman heat index, simplified WBGT,
  Humidex, etc.), each with different input requirements, assumptions, and
  limitations.
- **Decision:** Defer the selection of a specific heat-risk formula to the
  dedicated risk-engine module (Module 6+). The database stores only raw
  measurements and quality metadata in Module 2. Calculated indicators are
  not stored in the `sensor_readings` table.
- **Rationale:**
  - Temperature and humidity alone do not constitute a WBGT measurement.
  - The available sensor inputs depend on hardware confirmation (ADR-008).
  - Selecting arbitrary thresholds without domain review risks false claims.
  - Raw data must be preserved unchanged; calculated values are derived.
- **Consequences:** No heat-index column in `sensor_readings`. Computed
  indicators will be stored in a separate table or returned as API response
  fields with explicit formula identification, version, and limitations.
  The risk-engine module must document its chosen formula thoroughly.

---

## ADR-015: Application Factory and Centralized Error Envelopes in FastAPI

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** The FastAPI backend requires consistent initialization across development,
  testing, and production. Errors across all layers (validation, HTTP errors, application
  logic, unhandled exceptions) must conform to the Module 2 API error contract without
  leaking internal details or stack traces.
- **Decision:** Use an explicit application factory (`create_app(settings)`) that returns
  a configured `FastAPI` instance and mounts centralized exception handlers for
  `AppException`, `RequestValidationError`, `StarletteHTTPException`, and generic `Exception`.
- **Rationale:**
  - Facilitates isolated test runs without altering global process state.
  - Ensures all error responses strictly follow `{"error": {"code": "...", "message": "...", "details": [...]}}`.
  - Hides internal implementation details and stack traces from production clients on 500 errors.
- **Consequences:** All route-level exceptions must either inherit from `AppException` or
  use standard status codes caught by centralized handlers.

---

## ADR-016: Typed Environment Settings with Secret Masking via Pydantic Settings

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** Backend configuration must be environment-driven, support `.env` files,
  validate configuration types at startup, and protect secret credentials from accidental
  log or traceback leaks.
- **Decision:** Use `pydantic-settings` (`BaseSettings`) with `SecretStr` for credentials
  like `SECRET_KEY`, and field validators for comma-separated CORS origins and API prefix formatting.
- **Rationale:**
  - Guarantees fail-fast configuration validation on startup.
  - `SecretStr` prevents secret values from being exposed in logs, string formatting, or exceptions.
  - Safe development defaults allow immediate developer productivity without real production secrets.
- **Consequences:** Code accessing secret values must explicitly invoke `.get_secret_value()`.

---

## ADR-017: Distinct Semantics for Liveness (/health) and Readiness (/ready) Probes

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** Orchestration platforms and monitoring tools require separate probes to determine
  whether an API process is running (liveness) versus whether it is capable of serving traffic (readiness).
- **Decision:** Implement `GET /health` purely as a process liveness check, and `GET /ready`
  as a readiness check reflecting actual dependency state (in Module 3, external database is explicitly
  reported as `not_configured` without pretending to be connected).
- **Rationale:**
  - Prevents premature traffic delivery before dependent services are initialized.
  - Avoids false assertions about external dependencies like PostgreSQL in initial modules.
  - Aligns with cloud-native monitoring standards (Kubernetes, Docker health checks).
- **Consequences:** When database models and migrations are implemented in Module 4,
  the `/ready` probe must be extended with an active ping to the database connection pool.

---

## ADR-018: SQLAlchemy 2.0 Declarative Models with Dialect-Agnostic Variants

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** The system uses PostgreSQL 15+ in production with JSONB, UUID, and TIMESTAMPTZ
  data types. Fast, isolated unit tests and developer scratch test suites require in-memory
  execution without spinning up external database dependencies.
- **Decision:** Use SQLAlchemy 2.0 type-annotated `Mapped[...]` and `mapped_column(...)`,
  with `JSONB().with_variant(JSON(), "sqlite")` and `Uuid(as_uuid=True)`.
- **Rationale:**
  - Enables production PostgreSQL to leverage binary JSONB operators and native UUIDs.
  - Permits isolated unit tests to execute in memory without external database server requirements.
  - Eliminates type divergence between migration metadata and application ORM classes.
- **Consequences:** Advanced PostgreSQL-specific operators (e.g. JSONB containment `@>`) must
  only be invoked in repository paths targeted to PostgreSQL.

---

## ADR-019: Automated Database Driver Normalization for psycopg2

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** Standard deployment platforms, connection strings, and `.env` files supply
  URLs formatted as `postgresql://...` or `postgres://...`. In SQLAlchemy 2.0+, `postgresql://`
  defaults to `psycopg` (v3), causing import errors when `psycopg2-binary` is installed.
- **Decision:** Automatically normalize connection schemes in `build_engine()` and `alembic/env.py`
  from `postgresql://` and `postgres://` to `postgresql+psycopg2://`.
- **Rationale:**
  - Provides a seamless developer experience with standard PostgreSQL URLs.
  - Prevents deployment failures caused by subtle driver prefix mismatches.
  - Centralizes dialect resolution in engine initialization.
- **Consequences:** All PostgreSQL connections in the application consistently use `psycopg2`.

---

## ADR-020: Repository Abstraction for Persistence Separation

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** Business logic, telemetry ingestion, and route handlers should not construct
  raw SQL queries or manipulate SQLAlchemy sessions directly.
- **Decision:** Implement dedicated repository functions under `app.repositories` for
  `worksite`, `device`, `reading`, and `alert` operations.
- **Rationale:**
  - Decouples API route handlers and future background workers from database mechanics.
  - Encapsulates transaction boundaries, deduplication logic, and sorting orders in reusable functions.
  - Simplifies mocking and isolated testing in domain modules.
- **Consequences:** Future feature modules must access the database via repository abstractions
  rather than ad-hoc session queries.

---

## ADR-021: Sensor Hardware Abstraction Layer (HAL) and Safe Unconfigured Defaults

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** Hardware selection for ESP32 and environmental sensors is deliberately unconfirmed in Module 5.
  Prematurely committing to specific GPIO pinouts, I2C addresses, or proprietary sensor libraries risks
  introducing hardware conflicts and architectural coupling.
- **Decision:** Encapsulate physical sensor interactions behind an abstract C++ interface (`ISensor`).
  Provide a default `UnconfiguredSensor` adapter that fails safely, explicitly reporting `SENSOR_STATUS_UNCONFIGURED`
  and populating readings with `QUALITY_MISSING`. Prohibit simulated readings from masquerading as hardware data
  by enforcing a typed `ReadingSourceMode` enum (`SOURCE_MODE_HARDWARE` vs `SOURCE_MODE_SIMULATED`).
- **Rationale:**
  - Decouples firmware validation, alerting, and telemetry boundaries from physical hardware.
  - Enables full test coverage of firmware business logic on host machines without hardware emulators.
  - Eliminates the risk of false-positive testing where mock data is mistaken for actual sensor communication.
- **Consequences:** Concrete sensor drivers (e.g. SHT31, BME280) must implement `ISensor` once hardware
  is procured, without modifying validation, alerting, or serialization logic.

---

## ADR-022: Fail-Safe Local Alert Evaluation and Offline Unknown State

- **Status:** Accepted
- **Date:** 2026-10-24
- **Context:** Outdoor worker heat monitoring is a life-safety critical application. If a physical sensor
  fails, disconnects, reports non-finite numbers (NaN/Inf), or produces out-of-bounds readings, the local
  alert indicator must never misinform workers that conditions are safe (green). Furthermore, local alerts
  must evaluate deterministically without cloud or internet connectivity.
- **Decision:** Implement autonomous, on-device alert evaluation with an explicit `ALERT_LEVEL_UNKNOWN` fallback.
  Any missing measurement, bus error, non-finite float, or failed validation unconditionally transitions the
  alert state to `ALERT_LEVEL_UNKNOWN`. A stateful hysteresis deadband prevents rapid state fluttering on
  thermal boundaries. Provisional threshold values (35.0 °C caution, 40.0 °C danger) are strictly documented
  as scaffolding placeholders without claiming clinical or diagnostic validity.
- **Rationale:**
  - Fail-safe design ensures faulty hardware or unconfigured states can never be mistaken for safe conditions.
  - Zero network dependency ensures worker safety alerts operate reliably even in remote worksites with zero connectivity.
  - Clear separation between engineering placeholders and formal medical/occupational risk models protects project integrity.
- **Consequences:** Physical alert actuators (buzzers/LEDs) must indicate the `UNKNOWN` state distinctly
  (e.g., continuous amber pulse or diagnostic sequence) rather than turning off or displaying green.

---

## Template for Future Decisions

```markdown
## ADR-NNN: Title

- **Status:** Proposed | Accepted | Superseded by ADR-XXX | Amended
- **Date:** YYYY-MM-DD
- **Context:** What is the issue?
- **Decision:** What was decided?
- **Rationale:** Why this choice?
- **Consequences:** What are the trade-offs?
```


