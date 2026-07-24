# syntax=docker/dockerfile:1
# Multi-stage build (Sprint 15): a builder stage downloads/compiles wheels, and a
# slim runtime stage copies only the installed packages + app — smaller final
# image, better layer caching, and a non-root user for a hardened container.

# ---- Builder ---------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies into an isolated prefix so the runtime stage copies just
# the site-packages, not pip's caches or build tooling.
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# ---- Runtime ---------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

WORKDIR /app

# ffmpeg is the only OS dependency (frame extraction). curl is used by HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built dependencies from the builder stage.
COPY --from=builder /install /usr/local

# Run as an unprivileged user (least privilege).
RUN useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser . .
# Pre-create the runtime write dirs owned by appuser. /app itself is root-owned, so
# without this the non-root user cannot `mkdir /app/uploads` at request time — the
# clip save + frame extraction fail and readiness reports the upload dir degraded.
RUN mkdir -p /app/uploads/frames && chown -R appuser:appuser /app/uploads
USER appuser

EXPOSE 8000

# Container-level liveness probe (complements Render's healthCheckPath).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/api/health" || exit 1

# Honor $PORT (Render/Heroku inject it); default 8000 for local docker run.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
