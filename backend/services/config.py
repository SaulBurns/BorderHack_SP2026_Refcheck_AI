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
