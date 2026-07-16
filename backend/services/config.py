"""Centralized configuration (Sprint 7).

Single source of truth for every environment variable the backend reads and the
default values that were previously duplicated across modules (the provider
factory, detector registry, the pipeline, and the CLIs each re-typed `"mock"` /
`"claude_vision"` and their own env-name strings).

Design boundary: providers still read their *own* secrets inside `send_messages`
(encapsulation is intentional — see CLAUDE.md), but they reference the NAME
constants here instead of hardcoding magic strings. Nothing in this module reads
a secret at import time; callers read on demand so tests can set env vars freely.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Environment variable names
# ---------------------------------------------------------------------------

AI_PROVIDER_ENV = "AI_PROVIDER"
AI_MODEL_ENV = "AI_MODEL"
DETECTOR_ENV = "DETECTOR"
ANALYSIS_CACHE_ENV = "ANALYSIS_CACHE"

ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GEMINI_MODEL_ENV = "GEMINI_MODEL"

SUPABASE_URL_ENV = "SUPABASE_URL"
SUPABASE_SERVICE_ROLE_KEY_ENV = "SUPABASE_SERVICE_ROLE_KEY"
SUPABASE_CLIPS_BUCKET_ENV = "SUPABASE_CLIPS_BUCKET"
SUPABASE_VERDICTS_TABLE_ENV = "SUPABASE_VERDICTS_TABLE"

FRONTEND_ORIGIN_ENV = "FRONTEND_ORIGIN"
CORS_ORIGINS_ENV = "CORS_ORIGINS"

# ---------------------------------------------------------------------------
# Defaults (previously duplicated across modules)
# ---------------------------------------------------------------------------

DEFAULT_PROVIDER = "mock"
DEFAULT_DETECTOR = "claude_vision"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_SUPABASE_BUCKET = "clips"
DEFAULT_SUPABASE_TABLE = "verdicts"

_TRUTHY = {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Resolvers — the single place selection defaults are applied
# ---------------------------------------------------------------------------

def resolved_provider(explicit: str | None = None) -> str:
    """Provider key from an explicit arg, else AI_PROVIDER, else the default."""
    return (explicit or os.getenv(AI_PROVIDER_ENV) or DEFAULT_PROVIDER).strip().lower()


def resolved_detector(explicit: str | None = None) -> str:
    """Detector key from an explicit arg, else DETECTOR, else the default."""
    return (explicit or os.getenv(DETECTOR_ENV) or DEFAULT_DETECTOR).strip().lower()


def env_flag(name: str, default: bool = False) -> bool:
    """Interpret an env var as a boolean flag (1/true/yes/on)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY
