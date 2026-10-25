# HeatShield Bharat — React Frontend Foundation

The frontend application for **HeatShield Bharat**, an IoT-based environmental heat-monitoring and early-warning decision support system.

> **Current Status (Module 13):** End-to-End Integration and Automated Testing complete. Features comprehensive integration tests (`IntegrationE2E.test.tsx`) verifying route protection, unauthenticated redirects, live telemetry display with °C and % units, null handling ("Unavailable" without converting to zero), stale data warnings, and role-based action controls (supervisor acknowledge button vs viewer restricted notice). All 47 Vitest tests pass, with 0 TypeScript compilation errors and clean production builds.
>
> **Hardware Status:** The physical ESP32 microcontrollers and environmental sensor modules remain unpurchased. Telemetry freshness and device connectivity are strictly distinguished; no fabricated readings or fake devices are presented.


---

## Technical Specifications

- **Framework:** React 19
- **Language:** TypeScript 5.9+
- **Build Tool:** Vite 6
- **Router:** React Router v7
- **Styling:** Vanilla CSS with custom industrial safety design tokens and glassmorphic elements
- **Test Runner:** Vitest 4 with React Testing Library and Happy DOM
- **Linter:** Oxlint

---

## Directory Structure

```text
frontend/
├── public/
│   └── favicon.svg              # Shield logo favicon
├── src/
│   ├── app/
│   │   ├── App.tsx              # Route table and main layout integration
│   │   └── main.tsx             # Application bootstrap & DOM mount
│   ├── components/
│   │   ├── feedback/
│   │   │   ├── EmptyState.tsx   # Reusable empty collection / disconnected state
│   │   │   ├── ErrorState.tsx   # Reusable error alert with retry trigger
│   │   │   ├── LoadingState.tsx # Accessible loading spinner (role="status")
│   │   │   └── StatusBadge.tsx  # Accessible color + text + dot status tag
│   │   └── layout/
│   │       ├── AppLayout.tsx    # Semantic header, main, footer layout + skip-to-content link
│   │       ├── Header.tsx       # Brand navigation & live backend readiness probe badge
│   │       └── Footer.tsx       # Safety disclaimers & project hardware status
│   ├── features/
│   │   ├── alerts/
│   │   │   └── types.ts         # Module 8 alert and rule contracts
│   │   ├── devices/
│   │   │   └── types.ts         # Device domain types (noting future GET /devices route)
│   │   └── readings/
│   │       └── types.ts         # Telemetry & Module 7 heat-risk calculation contracts
│   ├── pages/
│   │   ├── AlertsPage.tsx       # Active alerts & rules list connecting to GET /api/v1/alerts
│   │   ├── DevicesPage.tsx      # Clearly labelled placeholder with honest unconfirmed hardware state
│   │   ├── HeatRiskCalculatorPage.tsx # Interactive testbench for POST /api/v1/readings/calculate-heat-index
│   │   ├── NotFoundPage.tsx     # 404 handler for unmatched routes
│   │   └── OverviewPage.tsx     # System overview with live backend probe & capability cards
│   ├── services/
│   │   ├── alertService.ts      # Alerts and rules API integration
│   │   ├── api.ts               # Generic type-safe HTTP client with timeout & error handling
│   │   ├── healthService.ts     # Health and live readiness checks (/health, /ready)
│   │   └── heatRiskService.ts   # Heat risk calculation API integration
│   ├── styles/
│   │   └── index.css            # Core design system tokens, typography, grid, buttons
│   └── test/
│       ├── Analytics.test.tsx   # Module 11 trend charts, summaries, gap detection
│       ├── apiClient.test.ts    # Generic API client error handling & timeout tests
│       ├── App.test.tsx         # UI rendering, navigation, and accessibility tests
│       ├── Auth.test.tsx        # Module 12 login forms, sessions, role authorization
│       ├── Dashboard.test.tsx   # Module 10 live monitoring, polling, and metric cards
│       ├── IntegrationE2E.test.tsx # Module 13 end-to-end flow, redirects, RBAC alert actions
│       └── setup.ts             # Vitest test setup with @testing-library/jest-dom
├── .env.example                 # Environment configuration template
├── index.html                   # HTML entry point with fonts & SEO meta tags
├── package.json                 # Pinned dependencies and execution scripts
├── tsconfig.app.json            # Strict TypeScript configuration
└── vite.config.ts               # Vite configuration with Vitest happy-dom integration
```

---

## Route Map

| Path | Component | Auth Required? | Purpose | Backend Integration |
| :--- | :--- | :---: | :--- | :--- |
| `/login` | `LoginPage` | Public | Sign in form with email & password validation and error alerts. | `POST /api/v1/auth/login` |
| `/` | `DashboardPage` | ✅ Protected | Live environmental monitoring, NWS heat index screening, active alerts, device inventory, and auto-refresh controls. | `GET /devices`, `GET /readings/latest`, `POST /readings/calculate-heat-index`, `GET /alerts` |
| `/overview` | `OverviewPage` | Public | System overview, module readiness, and architecture summary. | `GET /ready` & `GET /health` |
| `/analytics` | `AnalyticsPage` | ✅ Protected | Time-series trend charts, historical readings, summary statistics, and gap detection. | `GET /readings/history` & `GET /alerts` |
| `/devices` | `DevicesPage` | ✅ Protected | Hardware device nodes inventory & contracts. Displays honest procurement-pending state. | `GET /devices` |
| `/alerts` | `AlertsPage` | ✅ Protected | Active incidents list, episode deduplication, role-aware acknowledgement/resolution actions, and threshold rules. | `GET /alerts`, `GET /alert-rules`, `POST /alerts/{id}/acknowledge`, `POST /alerts/{id}/resolve` |
| `/calculator` | `HeatRiskCalculatorPage` | Public | Interactive testbench for Rothfusz/Steadman heat index calculation. | `POST /readings/calculate-heat-index` |
| `*` | `NotFoundPage` | Public | 404 Not Found error page with navigation back to overview. | None (client-side) |

---

## Live Refresh & Data Freshness Policy

- **Configurable Polling Intervals:** 10s, 15s (Default), 30s, 60s, or Paused (Manual refresh only).
- **Manual Refresh:** Keyboard-accessible "Refresh Now" button with loading spinner state and aria labels.
- **Request Overlap Guard:** Concurrent polling or rapid button clicks are debounced; pending requests do not overlap.
- **Unmount Cleanup:** Active interval timers are cleared automatically on component unmount.
- **Cached-Stale Retention:** If a background refresh fails after previous success, existing data is retained with an explicit warning banner (`role="alert"`) informing the user data is potentially stale.
- **Data Freshness Distinction:**
  - **Backend Reachable:** FastAPI `/ready` & `/health` probes return 200 OK.
  - **Device Seen:** `last_seen_at` within 5 minutes indicates recent device heartbeat.
  - **Reading Fresh:** Measured within 15 minutes (`staleThresholdMinutes`).
  - **Reading Stale:** Data older than 15 minutes displays an amber `Stale Data (Xm old)` badge.
  - **Reading Unavailable:** Explicitly rendered as "Unavailable" without assuming zero.
  - **Device Hardware Unconfirmed:** Zero physical boards attached; honest empty state.

---

## Environment Configuration

Copy `.env.example` to `.env` to configure your local development environment:

```bash
cp .env.example .env
```

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | URL pointing to the FastAPI backend API surface. |

> **Security Invariant:** All variables prefixed with `VITE_` are embedded into the client-side JavaScript bundle and are publicly visible in the browser. **NEVER** place API keys, private credentials, database secrets, or device authentication tokens in frontend `.env` files.

---

## Local Development Setup

### 1. Install Dependencies
```bash
npm install
```

### 2. Start the Development Server
```bash
npm run dev
```
The application will be served at `http://localhost:5173`.

### 3. Connect to Backend Server
Ensure the FastAPI backend is running on `http://localhost:8000`:
```bash
# In the backend directory:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The header status badge will automatically transition to **Connected (DB Ready)** upon successful connection.

---

## Automated Verification & Build Commands

| Command | Tool | Purpose | Status |
| :--- | :--- | :--- | :--- |
| `npm run typecheck` | `tsc --noEmit` | Strict TypeScript type validation across all components and tests. | ✅ 0 errors |
| `npm run test` | `vitest run` | Executes all 47 unit, component, and E2E integration tests. | ✅ 47 passed |
| `npm run lint` | `oxlint` | High-performance linter checking React and TypeScript rules. | ✅ 0 errors |
| `npm run build` | `tsc -b && vite build` | Produces an optimized, minified production bundle in `dist/`. | ✅ built in ~1.4s |

---

## Container Deployment (Docker / Podman + Nginx)

The frontend provides a multi-stage container build (`frontend/Dockerfile`):
1. **Build Stage:** `node:22-alpine` runs `npm ci` and `npm run build` (creating optimized SPA assets in `dist/`).
2. **Runtime Stage:** `nginx:1.27-alpine` serves static files, proxies `/api/` to the backend, provides SPA HTML5 history fallback (`try_files $uri $uri/ /index.html`), enables gzip compression, and attaches security headers.

### Build Frontend Image
```bash
podman build -t heatshield-frontend:latest -f Dockerfile .
```

### Run Frontend Container
```bash
podman run -d --name heatshield_ui \
  -p 80:80 \
  heatshield-frontend:latest
```

---

## Hardware Limitations Notice

- **Physical ESP32 Microcontrollers:** Board and sensor selection is in progress; physical microcontrollers have not yet been purchased or connected.
- **Simulation / Testbench:** End-to-end telemetry flow can be tested via `curl` against `POST /api/v1/readings` or via the built-in Risk Calculator page.

