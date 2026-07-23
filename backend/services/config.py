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

# Sprint 14 — opt-in provider optimizations (default OFF; behavior unchanged unless
# explicitly enabled, so demos and tests are safe by default).
#   ANTHROPIC_PROMPT_CACHE: cache the large, reused adjudicator/perception system
#     prompt with Anthropic prompt caching (cheaper + lower latency on repeats).
#   GEMINI_JSON_MODE: ask Gemini for `application/json` output (more reliable JSON
#     parsing). Trades off the private <thinking> scratchpad, so it is opt-in.
ANTHROPIC_PROMPT_CACHE_ENV = "ANTHROPIC_PROMPT_CACHE"
GEMINI_JSON_MODE_ENV = "GEMINI_JSON_MODE"

# Sprint 16B — structured outputs.
#   ANTHROPIC_STRUCTURED_OUTPUT: opt in to Anthropic's native `output_config.format`
#     structured output (default OFF). The default model (claude-sonnet-4-5) does not
#     guarantee support, so by default Anthropic uses "robust JSON mode" instead —
#     the JSON-only prompt + Pydantic validation + retry. Enable this only on a model
#     that supports structured outputs (e.g. Opus 4.8 / Sonnet 5 / Haiku 4.5).
#   STRUCTURED_OUTPUT_RETRIES: how many times a validation failure is retried before
#     the pipeline degrades to the mock fallback (default 1).
ANTHROPIC_STRUCTURED_OUTPUT_ENV = "ANTHROPIC_STRUCTURED_OUTPUT"
STRUCTURED_OUTPUT_RETRIES_ENV = "STRUCTURED_OUTPUT_RETRIES"

DEFAULT_STRUCTURED_OUTPUT_RETRIES = 1

# Sprint 16D — provider-communication reliability. Transport-level retry with
# exponential backoff for *transient* provider failures (429/5xx/timeout/dropped
# connection); auth, bad-request, and validation failures are never retried.
#   PROVIDER_MAX_RETRIES: retries after the first attempt (2 → 3 total attempts).
#   PROVIDER_BACKOFF_BASE_SECONDS / PROVIDER_BACKOFF_MAX_SECONDS: expo backoff bounds.
#   PROVIDER_TIMEOUT_SECONDS: per-request socket timeout.
PROVIDER_MAX_RETRIES_ENV = "PROVIDER_MAX_RETRIES"
PROVIDER_BACKOFF_BASE_SECONDS_ENV = "PROVIDER_BACKOFF_BASE_SECONDS"
PROVIDER_BACKOFF_MAX_SECONDS_ENV = "PROVIDER_BACKOFF_MAX_SECONDS"
PROVIDER_TIMEOUT_SECONDS_ENV = "PROVIDER_TIMEOUT_SECONDS"

DEFAULT_PROVIDER_MAX_RETRIES = 2
DEFAULT_PROVIDER_BACKOFF_BASE_SECONDS = 0.5
DEFAULT_PROVIDER_BACKOFF_MAX_SECONDS = 8.0
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 90.0

# Sprint 17A — provider router. With AI_PROVIDER=router, each pipeline task selects
# its own provider: perception (vision-heavy) and adjudication (text reasoning) can
# use different backends. Each task env falls back to ROUTER_DEFAULT_PROVIDER, which
# defaults to "anthropic" — so AI_PROVIDER=router behaves like anthropic out of the box.
ROUTER_DEFAULT_PROVIDER_ENV = "ROUTER_DEFAULT_PROVIDER"
ROUTER_PERCEPTION_PROVIDER_ENV = "ROUTER_PERCEPTION_PROVIDER"
ROUTER_ADJUDICATION_PROVIDER_ENV = "ROUTER_ADJUDICATION_PROVIDER"

DEFAULT_ROUTER_PROVIDER = "anthropic"

# Task identifiers the pipeline routes on (also passed to `route()`).
TASK_PERCEPTION = "perception"
TASK_ADJUDICATION = "adjudication"

# task -> the env var naming its provider.
_ROUTER_TASK_ENV = {
    TASK_PERCEPTION: ROUTER_PERCEPTION_PROVIDER_ENV,
    TASK_ADJUDICATION: ROUTER_ADJUDICATION_PROVIDER_ENV,
}

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


def router_default_provider() -> str:
    """The provider a router task falls back to (default "anthropic")."""
    return (os.getenv(ROUTER_DEFAULT_PROVIDER_ENV) or DEFAULT_ROUTER_PROVIDER).strip().lower()


def router_provider_for(task: str | None) -> str:
    """Provider name the router should use for `task`.

    Reads the task's env var (ROUTER_PERCEPTION_PROVIDER / ROUTER_ADJUDICATION_PROVIDER),
    falling back to ROUTER_DEFAULT_PROVIDER for an unset var or an unknown task.
    """
    env = _ROUTER_TASK_ENV.get((task or "").strip().lower())
    value = os.getenv(env) if env else None
    return (value or router_default_provider()).strip().lower()


def env_flag(name: str, default: bool = False) -> bool:
    """Interpret an env var as a boolean flag (1/true/yes/on)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY


def env_int(name: str, default: int) -> int:
    """Interpret an env var as an int, falling back to `default` on unset/invalid."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    """Interpret an env var as a float, falling back to `default` on unset/invalid."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default
