# ==============================================================================
# Multi-stage Dockerfile for Hedgewar Hospital Management System
# Compliant with CIS Docker Benchmark: Non-root user, minimal attack surface
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Dependencies
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Runtime Image
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=hms \
    FLASK_ENV=production \
    PORT=5000

# Install minimal runtime dependencies (curl for container health probes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root system user and group (CIS Docker 4.1)
RUN groupadd -g 10001 hmsgroup && \
    useradd -u 10001 -g hmsgroup -s /sbin/nologin -M hmsuser

WORKDIR /app

# Copy application source code and set ownership
COPY --chown=hmsuser:hmsgroup . /app

# Ensure uploads and logs directory exists with appropriate permissions
RUN mkdir -p /app/uploads /app/logs && \
    chown -R hmsuser:hmsgroup /app/uploads /app/logs

# Switch to non-root execution
USER hmsuser

EXPOSE 5000

# Container liveness check (R-02)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/healthz || exit 1

# Production WSGI server (R-06)
CMD ["gunicorn", "--config", "gunicorn.conf.py", "hms:create_app()"]
