"""Health & readiness reporting (Sprint 15).

Two distinct signals, following the standard liveness/readiness split:

- **Liveness** (`/api/health`) — the process is up. Cheap, dependency-free, and
  kept backward compatible (still returns `status: "ok"`), so Render's health check
  and any existing monitor keep working.
- **Readiness** (`/api/health/ready`) — the process can actually serve analyses:
  the AI provider is configured, `ffmpeg` is available for frame extraction, and the
  upload dir is writable. Degrades gracefully — a failing check reports `degraded`
  with per-check detail rather than raising.

Pure functions returning plain dicts, so they are unit-testable without HTTP.
"""

from __future__ import annotations

import os
import shutil
import time

from services import config

# Process start time for an uptime signal (module import ~= process start).
_STARTED_AT = time.time()

APP_VERSION_ENV = "APP_VERSION"
APP_ENV_ENV = "APP_ENV"


def app_version() -> str:
    return os.getenv(APP_VERSION_ENV, "dev")


def app_environment() -> str:
    return os.getenv(APP_ENV_ENV, "development")


def uptime_seconds() -> float:
    return round(time.time() - _STARTED_AT, 3)


def liveness() -> dict:
    """Fast, always-ok liveness payload (backward-compatible superset)."""
    return {
        "status": "ok",
        "message": "RefCheck AI backend is running",
        "version": app_version(),
        "environment": app_environment(),
        "uptime_seconds": uptime_seconds(),
    }


def _check_provider() -> dict:
    provider = config.resolved_provider()
    if provider == "mock":
        return {"ok": True, "detail": "mock provider (no key required)"}
    key_env = {
        "anthropic": config.ANTHROPIC_API_KEY_ENV,
        "gemini": config.GEMINI_API_KEY_ENV,
    }.get(provider)
    if key_env is None:
        return {"ok": False, "detail": f"unknown provider {provider!r}"}
    has_key = bool(os.getenv(key_env))
    return {
        "ok": has_key,
        "detail": f"{provider}: {'API key present' if has_key else 'API key missing (will degrade to mock)'}",
    }


def _check_ffmpeg() -> dict:
    present = shutil.which("ffmpeg") is not None
    return {
        "ok": present,
        "detail": "ffmpeg available" if present else "ffmpeg missing (frame extraction degrades to mock)",
    }


def _check_upload_dir() -> dict:
    try:
        from services.video_processor import UPLOAD_DIR

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        writable = os.access(UPLOAD_DIR, os.W_OK)
        return {"ok": writable, "detail": f"{UPLOAD_DIR} {'writable' if writable else 'not writable'}"}
    except Exception as exc:  # never raise from a health check
        return {"ok": False, "detail": f"upload dir error: {type(exc).__name__}"}


def readiness() -> dict:
    """Readiness payload with per-dependency checks.

    `status` is `ready` only when every check passes; otherwise `degraded` (the app
    still serves — it falls back to the mock path — but operators should know).
    """
    checks = {
        "provider": _check_provider(),
        "ffmpeg": _check_ffmpeg(),
        "upload_dir": _check_upload_dir(),
    }
    ready = all(check["ok"] for check in checks.values())
    return {
        "status": "ready" if ready else "degraded",
        "version": app_version(),
        "environment": app_environment(),
        "uptime_seconds": uptime_seconds(),
        "checks": checks,
    }
