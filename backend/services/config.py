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

# Sprint 18A — YOLO detector configuration. The `yolov8`/`hybrid` detectors run
# Ultralytics YOLO; these vars make the weights, tracker, and thresholds fully
# configurable without code changes. Defaults track the latest stable Ultralytics
# flagship (YOLO26, Jan 2026). The `yolov8` registry key is kept as a stable role
# identifier; the concrete model that ran is always reported on `RawDetections.model`.
YOLO_MODEL_ENV = "YOLO_MODEL"
YOLO_CONFIDENCE_ENV = "YOLO_CONFIDENCE"
YOLO_TRACKER_ENV = "YOLO_TRACKER"
YOLO_TRACKING_ENV = "YOLO_TRACKING"

ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GEMINI_MODEL_ENV = "GEMINI_MODEL"

# Sprint 17C — graceful failover. When the selected real provider fails a call
# (auth/bad-request/SDK-missing, or transient retries exhausted), the pipeline
# fails over to this provider before degrading to the offline mock. Unset (default)
# = no failover, i.e. the unchanged behavior (a hard failure degrades to mock).
PROVIDER_FALLBACK_ENV = "PROVIDER_FALLBACK"

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

# Sprint 17B — per-agent providers AND models. Each pipeline stage can now also pin
# its own model. The concise, spec-facing names take precedence over the legacy
# Sprint 17A ROUTER_* provider vars (which stay valid for backward compatibility):
#   perception   -> PERCEPTION_PROVIDER  + PERCEPTION_MODEL
#   adjudication -> ADJUDICATOR_PROVIDER + ADJUDICATOR_MODEL
# A model left unset means "let the resolved provider pick its own model" (its
# AI_MODEL/GEMINI_MODEL env or built-in default), so out of the box nothing changes.
PERCEPTION_PROVIDER_ENV = "PERCEPTION_PROVIDER"
PERCEPTION_MODEL_ENV = "PERCEPTION_MODEL"
ADJUDICATOR_PROVIDER_ENV = "ADJUDICATOR_PROVIDER"
ADJUDICATOR_MODEL_ENV = "ADJUDICATOR_MODEL"

DEFAULT_ROUTER_PROVIDER = "anthropic"

# Task identifiers the pipeline routes on (also passed to `route()`).
TASK_PERCEPTION = "perception"
TASK_ADJUDICATION = "adjudication"

# task -> the env vars naming its provider, highest precedence first. The Sprint 17B
# name wins over the legacy Sprint 17A name; either falls back to ROUTER_DEFAULT_PROVIDER.
_ROUTER_TASK_PROVIDER_ENVS = {
    TASK_PERCEPTION: (PERCEPTION_PROVIDER_ENV, ROUTER_PERCEPTION_PROVIDER_ENV),
    TASK_ADJUDICATION: (ADJUDICATOR_PROVIDER_ENV, ROUTER_ADJUDICATION_PROVIDER_ENV),
}

# task -> the env var naming its model (Sprint 17B).
_ROUTER_TASK_MODEL_ENV = {
    TASK_PERCEPTION: PERCEPTION_MODEL_ENV,
    TASK_ADJUDICATION: ADJUDICATOR_MODEL_ENV,
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

# Sprint 18A — YOLO detector defaults. Upgraded from YOLOv8-nano (`yolov8n.pt`) to
# the latest stable Ultralytics flagship, YOLO26-nano. `bytetrack.yaml` remains the
# standard Ultralytics tracker config name across the 8.x line.
DEFAULT_YOLO_MODEL = "yolo26n.pt"
DEFAULT_YOLO_CONFIDENCE = 0.25
DEFAULT_YOLO_TRACKER = "bytetrack.yaml"

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


def resolved_yolo_model(explicit: str | None = None) -> str:
    """YOLO weights id from an explicit arg, else YOLO_MODEL, else the default (Sprint 18A)."""
    return (explicit or os.getenv(YOLO_MODEL_ENV) or DEFAULT_YOLO_MODEL).strip()


def resolved_yolo_confidence(explicit: float | None = None) -> float:
    """YOLO confidence threshold from an explicit arg, else YOLO_CONFIDENCE, else default."""
    if explicit is not None:
        return explicit
    return env_float(YOLO_CONFIDENCE_ENV, DEFAULT_YOLO_CONFIDENCE)


def resolved_yolo_tracker(explicit: str | None = None) -> str:
    """YOLO tracker config from an explicit arg, else YOLO_TRACKER, else the default."""
    return (explicit or os.getenv(YOLO_TRACKER_ENV) or DEFAULT_YOLO_TRACKER).strip()


def resolved_yolo_tracking(explicit: bool | None = None) -> bool:
    """Whether YOLO runs with tracking (persistent track_ids), default on (Sprint 18A)."""
    if explicit is not None:
        return explicit
    return env_flag(YOLO_TRACKING_ENV, True)


def fallback_provider() -> str | None:
    """The failover provider name (Sprint 17C), or None when none is configured."""
    value = os.getenv(PROVIDER_FALLBACK_ENV)
    if value and value.strip():
        return value.strip().lower()
    return None


# provider key -> (model env var, default model). The single source of truth for
# which env names/defaults each provider's model resolves from (Sprint 17C).
_PROVIDER_MODEL_ENV = {
    "anthropic": (AI_MODEL_ENV, DEFAULT_ANTHROPIC_MODEL),
    "gemini": (GEMINI_MODEL_ENV, DEFAULT_GEMINI_MODEL),
}


def resolved_model_for_provider(name: str) -> str | None:
    """The model id a leaf provider resolves to (its env override or default).

    Returns None for providers with no model notion (e.g. the mock). Used by
    startup validation and diagnostics so operators can see exactly which model a
    given provider will call, without instantiating the provider.
    """
    entry = _PROVIDER_MODEL_ENV.get((name or "").strip().lower())
    if entry is None:
        return None
    env_name, default = entry
    return os.getenv(env_name) or default


def router_default_provider() -> str:
    """The provider a router task falls back to (default "anthropic")."""
    return (os.getenv(ROUTER_DEFAULT_PROVIDER_ENV) or DEFAULT_ROUTER_PROVIDER).strip().lower()


def router_provider_for(task: str | None) -> str:
    """Provider name the router should use for `task`.

    Reads the task's env vars in precedence order — the Sprint 17B name
    (PERCEPTION_PROVIDER / ADJUDICATOR_PROVIDER) then the legacy Sprint 17A name
    (ROUTER_PERCEPTION_PROVIDER / ROUTER_ADJUDICATION_PROVIDER) — falling back to
    ROUTER_DEFAULT_PROVIDER for an unset var or an unknown task.
    """
    for env in _ROUTER_TASK_PROVIDER_ENVS.get((task or "").strip().lower(), ()):
        value = os.getenv(env)
        if value and value.strip():
            return value.strip().lower()
    return router_default_provider()


def router_model_for(task: str | None) -> str | None:
    """Model id the router should pin for `task`, or None to let the provider decide.

    Reads the task's model env var (PERCEPTION_MODEL / ADJUDICATOR_MODEL). Returns
    None when unset/blank so the resolved provider falls back to its own model
    (AI_MODEL/GEMINI_MODEL or built-in default) — the unchanged Sprint 17A behavior.
    Model ids are case-sensitive, so the value is only stripped, never lowercased.
    """
    env = _ROUTER_TASK_MODEL_ENV.get((task or "").strip().lower())
    value = os.getenv(env) if env else None
    if value and value.strip():
        return value.strip()
    return None


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
