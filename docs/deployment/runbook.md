# HeatShield Bharat — Operational Deployment Runbook (Module 14)

**Document Version:** 1.0.0  
**Target Environment:** Multi-Container Production / Staging / Local Demonstration  
**Stack:** React 19 + TypeScript 5.9, FastAPI (Python 3.12+), PostgreSQL 15+, Nginx, Podman / Docker Compose  
**Classification:** Operational Runbook & System Architecture Guide  

---

## 1. System Architecture & Topology

HeatShield Bharat is deployed as an isolated multi-tier container network. The architecture enforces least-privilege networking where the persistence layer is inaccessible from the public internet.

```
                            ┌─────────────────────────────────────────┐
                            │           Client Web Browser            │
                            └────────────────────┬────────────────────┘
                                                 │ HTTP / HTTPS (Port 80 / 443)
                                                 ▼
                            ┌─────────────────────────────────────────┐
                            │       heatshield-frontend (Nginx)       │
                            │  - Serves compiled React 19 SPA bundle  │
                            │  - SPA client fallback to /index.html   │
                            │  - Proxies /api/ requests to backend    │
                            │  - Security headers & gzip compression  │
                            └────────────────────┬────────────────────┘
                                                 │ Internal Bridge Network
                                                 │ (heatshield-net:8000)
                                                 ▼
                            ┌─────────────────────────────────────────┐
                            │       heatshield-backend (FastAPI)      │
                            │  - Non-root user: heatshield (UID 10001)│
                            │  - ASGI Server: Uvicorn multi-worker    │
                            │  - Explicit pre-startup migrations      │
                            │  - Liveness (/health) & Ready (/ready)  │
                            └────────────────────┬────────────────────┘
                                                 │ Internal Bridge Network
                                                 │ (heatshield-net:5432)
                                                 ▼
                            ┌─────────────────────────────────────────┐
                            │       heatshield-postgres (PG 15)       │
                            │  - Persistent named volume (db_data)    │
                            │  - Zero public port exposure by default │
                            │  - Pre-ping connection health check     │
                            └─────────────────────────────────────────┘
```

---

## 2. Prerequisites & Software Versions

| Component | Minimum Required Version | Recommended Version | Purpose |
|---|---|---|---|
| **Operating System** | Linux (Ubuntu 22.04+, Debian 12+, RHEL 9+) | Debian 12 Bookworm / Ubuntu 24.04 LTS | Host runtime |
| **Container Engine** | Podman 4.5+ or Docker Engine 24.0+ | Podman 5.8+ or Docker 26.0+ | Container orchestration |
| **Compose Tool** | Docker Compose v2.20+ or Podman Compose | Docker Compose v2.27+ | Multi-service lifecycle |
| **Python (Local dev)**| Python 3.11+ | Python 3.12 | Backend development & migrations |
| **Node.js (Local dev)**| Node.js 20 LTS | Node.js 22 LTS | Frontend compilation & testing |
| **PostgreSQL** | PostgreSQL 15 | PostgreSQL 15 Alpine | Relational persistence |

---

## 3. Environment Variables Reference

Environment configurations are separated into `.env.production` (production deployment) and local `.env` files.

> [!CAUTION]
> **Zero Committed Secrets:** Never commit real passwords, JWT secrets, or cryptographic keys to Git. All production secrets must be generated at deployment time.

| Variable | Required in Prod? | Default (Dev) | Description & Constraints |
|---|:---:|---|---|
| `APP_ENV` | **Yes** | `development` | Deployment environment (`production`, `staging`, `development`, `testing`). In `production`, strict validation invariants are enforced. |
| `DEBUG` | **Yes** | `true` (dev) | Must be `false` in production. Setting to `true` in production aborts startup. |
| `SECRET_KEY` | **Yes** | *insecure default* | Cryptographic signing key for JWT access tokens. Must be at least 32 high-entropy characters. Default key is rejected at startup in production. |
| `POSTGRES_USER` | **Yes** | `heatshield` | Database user account name. |
| `POSTGRES_PASSWORD` | **Yes** | *None* | Database user password. Must be a strong, non-empty secret. |
| `POSTGRES_DB` | **Yes** | `heatshield_prod` | Relational database catalog name. |
| `DATABASE_URL` | **Yes** | *None* | Connection URL: `postgresql://<user>:<pw>@postgres:5432/<db>`. |
| `PORT` | No | `80` | Public HTTP port exposed on host by Nginx. |
| `CORS_ORIGINS` | **Yes** | `http://localhost:5173` | Comma-separated list of allowed origins. Wildcard `*` is strictly forbidden in production. |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `RUN_MIGRATIONS` | No | `true` | If `true`, runs `alembic upgrade head` before Uvicorn starts. |
| `BACKEND_WORKERS` | No | `2` | Number of Uvicorn worker processes. Recommended: `(2 * CPU cores) + 1`. |
| `VITE_API_BASE_URL` | No | `/api/v1` | Frontend build-time variable for API base route. When behind Nginx reverse proxy, `/api/v1` operates seamlessly without CORS. |

### Generating Cryptographic Secrets
Run this on the host to generate a production secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 4. Database Provisioning & Migrations

Database migrations are managed via **Alembic** and SQLAlchemy 2.0.

### 4.1 Explicit Migration Execution
In containerized environments, migrations execute automatically during startup via `backend/scripts/start.sh` before traffic is accepted.

To run migrations manually outside Docker:
```bash
cd backend
source .venv/bin/activate
DATABASE_URL="postgresql://user:password@localhost:5432/heatshield" alembic upgrade head
```

### 4.2 Inspecting Migration History
```bash
cd backend
alembic current
alembic history --verbose
```

### 4.3 Data Preservation & Upgrade Policy
- All migrations (`0001_initial_schema`, `0002_add_device_api_key_hash`) are purely additive and preserve existing worksites, devices, sensor readings, and users.
- Never run `Base.metadata.drop_all()` in production environments.
- Downgrades are tested: `alembic downgrade -1`.

---

## 5. Deployment Procedures (Docker & Docker Compose)

### 5.1 Step 1: Prepare Environment Configuration
Create `.env.production` on the production server based on `.env.production.example`:
```bash
cp .env.production.example .env.production
chmod 600 .env.production
```
Edit `.env.production` and populate `POSTGRES_PASSWORD`, `SECRET_KEY`, and `CORS_ORIGINS`.

### 5.2 Step 2: Build Container Images
Using Docker Compose:
```bash
docker compose --env-file .env.production build
```
Using Podman directly:
```bash
podman build -t heatshield-backend:latest ./backend
podman build -t heatshield-frontend:latest ./frontend
```

### 5.3 Step 3: Launch Services in Background
```bash
docker compose --env-file .env.production up -d
```

### 5.4 Step 4: Verify Service Health
```bash
docker compose ps
```
All services (`heatshield-postgres`, `heatshield-backend`, `heatshield-frontend`) should display `healthy`.

### 5.5 Step 5: Provision Initial Administrative User
Run the provisioning CLI in the running backend container to generate an initial admin officer account without hardcoding credentials:
```bash
docker compose exec backend python -m app.cli.provision_admin \
    --email "admin.officer@heatshield.gov.in" \
    --name "State Heat Safety Administrator" \
    --password "SecureAdminPassword2026!"
```

---

## 6. Health Checks & Verification Probes

HeatShield Bharat implements 3 distinct health levels:

### 6.1 Liveness Probe (`GET /health`)
- **URL:** `http://<host>/api/v1/health` (or `http://backend:8000/health`)
- **Purpose:** Verifies that the FastAPI process is alive and responding.
- **Expected Status:** `200 OK`
- **Response Format:**
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-10-25T12:00:00Z",
    "version": "0.1.0"
  }
  ```

### 6.2 Readiness Probe (`GET /ready`)
- **URL:** `http://<host>/api/v1/ready` (or `http://backend:8000/ready`)
- **Purpose:** Actively verifies database connectivity and schema readiness.
- **Expected Status:** `200 OK` (when database is reachable) or `503 Service Unavailable` (if database connection fails).
- **Response Format:**
  ```json
  {
    "status": "ready",
    "timestamp": "2026-10-25T12:00:00Z",
    "version": "0.1.0",
    "services": {
      "api": "ready",
      "database": "connected"
    }
  }
  ```

### 6.3 Device Status (Telemetry Records)
- Device connectivity is queried via `GET /api/v1/devices` and `GET /api/v1/readings/latest`.
- **Invariant:** A healthy `/health` or `/ready` backend probe does **not** indicate that physical ESP32 nodes are connected. Sensor connectivity is evaluated exclusively on real persisted telemetry records (`last_seen_at` within 5 minutes).

---

## 7. Logging & Operational Troubleshooting

### 7.1 Inspecting Container Logs
```bash
# Tail all logs
docker compose logs -f

# Inspect backend service logs
docker compose logs -f backend

# Inspect database logs
docker compose logs -f postgres

# Inspect frontend/Nginx access & error logs
docker compose logs -f frontend
```

### 7.2 Common Operational Errors & Resolutions

#### 1. Backend Fails to Start with `ValidationError: DEBUG must be set to False`
- **Root Cause:** `APP_ENV=production` is active, but `DEBUG=true` is set.
- **Resolution:** Set `DEBUG=false` in `.env.production`.

#### 2. Backend Fails with `ValidationError: Default or insecure SECRET_KEY cannot be used`
- **Root Cause:** Production mode detected the development fallback secret key.
- **Resolution:** Generate a high-entropy secret (`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`) and update `SECRET_KEY` in `.env.production`.

#### 3. Backend Reports `503 Service Unavailable` on `/ready`
- **Root Cause:** PostgreSQL is initializing, restarting, or credentials in `DATABASE_URL` do not match PostgreSQL container settings.
- **Resolution:** Check PostgreSQL logs (`docker compose logs postgres`). Verify database container has passed its health check.

#### 4. Frontend Shows "Connection Refused" or "Failed to Retrieve Telemetry"
- **Root Cause:** Backend service is not reachable by Nginx.
- **Resolution:** Verify both containers are attached to `heatshield-net`. Confirm `docker compose exec frontend wget -qO- http://backend:8000/health` returns `healthy`.

---

## 8. Backup & Disaster Recovery Procedures

### 8.1 Automated Database Backup
Run `pg_dump` inside the running PostgreSQL container to generate an atomic SQL archive:
```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker compose exec postgres pg_dump -U heatshield_admin heatshield_production > backup_heatshield_${TIMESTAMP}.sql
gzip backup_heatshield_${TIMESTAMP}.sql
```

### 8.2 Database Restoration
```bash
# 1. Uncompress backup
gunzip backup_heatshield_YYYYMMDD_HHMMSS.sql.gz

# 2. Restore into target database
docker compose exec -T postgres psql -U heatshield_admin -d heatshield_production < backup_heatshield_YYYYMMDD_HHMMSS.sql
```

---

## 9. Secret Rotation Guidance

### Rotating the `SECRET_KEY` (JWT Signing Key)
1. Generate a new 32+ character key: `NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")`.
2. Update `SECRET_KEY` in `.env.production`.
3. Restart backend: `docker compose restart backend`.
4. *Impact:* Existing active user JWT sessions will expire immediately and require users to sign in again at `/login`. IoT device pre-shared keys are unaffected (stored as per-device SHA-256 hashes in database).

### Rotating Device Pre-Shared Keys
Device tokens are stored as salted SHA-256 hashes in `devices.api_key_hash`.
To rotate a device key:
1. Generate new token for device: `HS_DEVICE_TOKEN_NEW`.
2. Compute SHA-256 hash.
3. Update `devices` row for target `device_code`.
4. Flash the new token into the physical ESP32 firmware non-volatile storage (NVS).

---

## 10. Hardware Boundary & Known Limitations

- **Physical Microcontrollers & Sensors:** Unpurchased. Physical hardware tests remain explicitly **BLOCKED**.
- **No Cloud Account Assumed:** The deployment artifacts are self-contained and run on standard Linux/Docker environments. Deployment to AWS ECS, GCP Cloud Run, or Azure App Service requires providing cloud-specific credentials and DNS provisioning outside this repository.
