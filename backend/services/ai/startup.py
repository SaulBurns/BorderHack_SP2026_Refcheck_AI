"""AI provider startup validation, dependency probes & config summary (Sprint 17C).

Production hardening for the provider layer — especially Gemini, whose SDK is an
optional dependency. These are pure, side-effect-free helpers (no network, no
client creation, no secret logging) shared by:

- startup (`main.py`) — logs any misconfiguration warnings once, loudly, at boot;
- readiness (`services/health.py`) — turns the same checks into a 200/503 signal;
- diagnostics — `ai_config_summary()` exposes the active provider/model/fallback.

Keeping this in one module means "is provider X usable?" and "which model will it
call?" are answered the same way everywhere, instead of re-derived per call site.
"""

from __future__ import annotations

import importlib.util
import os

from services import config
from services.ai import factory


def gemini_sdk_available() -> bool:
    """True when the optional `google-genai` SDK is importable (no import executed).

    The canonical probe. `GeminiProvider.sdk_available()` delegates here, and the
    validation/diagnostics helpers below reach it through that class method (one
    seam), so the whole layer answers "is Gemini installed?" the same way.
    """
    try:
        return importlib.util.find_spec("google.genai") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _gemini_available() -> bool:
    """Ask the provider (which delegates to `gemini_sdk_available`) — one seam."""
    from services.ai.providers.gemini_provider import GeminiProvider

    return GeminiProvider.sdk_available()


def _has_key(provider: str) -> bool:
    key_env = {
        "anthropic": config.ANTHROPIC_API_KEY_ENV,
        "gemini": config.GEMINI_API_KEY_ENV,
    }.get(provider)
    return key_env is None or bool(os.getenv(key_env))


def provider_status(name: str) -> tuple[bool, str]:
    """Whether leaf provider `name` is fully usable, with a human-readable detail.

    Checks, in order: the provider is registered, its API key is present (mock is
    keyless), and — for Gemini — the `google-genai` SDK is installed. `router` is
    not a leaf and must be expanded by the caller (see `validate_ai_config`).
    """
    name = (name or "").strip().lower()
    if name == "mock":
        return True, "no key required"
    if name not in factory.supported_providers() or name == "router":
        return False, "unknown provider"
    if not _has_key(name):
        return False, "API key missing (will degrade to mock)"
    if name == "gemini" and not _gemini_available():
        return False, "google-genai SDK not installed"
    model = config.resolved_model_for_provider(name)
    return True, f"ready ({model})" if model else "ready"


def _leaf_providers(provider: str) -> list[str]:
    """The concrete providers a top-level AI_PROVIDER resolves to (expands router)."""
    if provider == "router":
        return [
            config.router_provider_for(task)
            for task in (config.TASK_PERCEPTION, config.TASK_ADJUDICATION)
        ]
    return [provider]


def validate_ai_config() -> list[str]:
    """Return human-readable warnings for a misconfigured AI provider setup.

    Empty list == healthy. Non-fatal by design: the pipeline still degrades to the
    mock at request time, but operators should see the problem at boot. Validates
    the selected provider (each leg of a router), its key/SDK, and any configured
    `PROVIDER_FALLBACK`.
    """
    warnings: list[str] = []
    provider = config.resolved_provider()
    if provider not in factory.supported_providers():
        return [
            f"AI_PROVIDER='{provider}' is not supported; "
            f"expected one of {factory.supported_providers()}"
        ]
    for name in dict.fromkeys(_leaf_providers(provider)):  # dedupe, keep order
        ok, detail = provider_status(name)
        if not ok:
            where = f" (routed from AI_PROVIDER=router)" if provider == "router" else ""
            warnings.append(f"provider '{name}'{where}: {detail}")
    fallback = config.fallback_provider()
    if fallback:
        if fallback not in factory.supported_providers():
            warnings.append(f"PROVIDER_FALLBACK='{fallback}' is not a supported provider")
        else:
            ok, detail = provider_status(fallback)
            if not ok:
                warnings.append(f"fallback provider '{fallback}': {detail}")
    return warnings


def ai_config_summary() -> dict:
    """A compact, secret-free description of the active AI provider configuration."""
    provider = config.resolved_provider()
    summary: dict = {
        "provider": provider,
        "fallback": config.fallback_provider(),
    }
    if provider == "router":
        summary["routes"] = {
            task: {
                "provider": config.router_provider_for(task),
                "model": config.router_model_for(task),
            }
            for task in (config.TASK_PERCEPTION, config.TASK_ADJUDICATION)
        }
    else:
        summary["model"] = config.resolved_model_for_provider(provider)
    if "gemini" in _leaf_providers(provider) or config.fallback_provider() == "gemini":
        summary["gemini_sdk_available"] = _gemini_available()
    return summary
