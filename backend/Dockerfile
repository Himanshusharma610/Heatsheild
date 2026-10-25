# ==============================================================================
# HeatShield Bharat — Backend Production Container Image
# Multi-stage, minimal, non-root Python 3.12 image for FastAPI ASGI Service
# ==============================================================================

# Stage 1: Build virtual environment with compiled wheels
FROM docker.io/library/python:3.12-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Minimal runtime image
FROM docker.io/library/python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Install runtime dependencies only (curl for healthcheck, libpq5 for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user and group
RUN groupadd -g 10001 heatshield && \
    useradd -u 10001 -g heatshield -s /bin/bash -m heatshield

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy backend application source and database migration assets
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
COPY scripts ./scripts

# Set permissions
RUN chmod +x ./scripts/*.sh && \
    chown -R heatshield:heatshield /app

USER heatshield

EXPOSE 8000

# Liveness health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./scripts/start.sh"]
