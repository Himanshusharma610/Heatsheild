#!/usr/bin/env bash
# ==============================================================================
# HeatShield Bharat — Backend Production Container Entrypoint
# ==============================================================================
set -euo pipefail

echo "================================================================="
echo " HeatShield Bharat Backend — Production ASGI Server Initialization"
echo "================================================================="

# Run database migrations if configured and requested (default: true if DATABASE_URL is set)
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"

if [ "${RUN_MIGRATIONS}" = "true" ] && [ -n "${DATABASE_URL:-}" ]; then
    echo "Running explicit database migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "Database migrations applied successfully."
else
    echo "Skipping automatic pre-flight migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS})."
fi

WORKERS="${WORKERS:-2}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "Starting Uvicorn ASGI server on ${HOST}:${PORT} with ${WORKERS} worker(s)..."
exec uvicorn app.main:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --workers "${WORKERS}"
