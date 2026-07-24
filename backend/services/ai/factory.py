"""Provider factory — selects a provider from the AI_PROVIDER env var.

Adding a future provider (OpenAI, Azure, Grok, Ollama, ...) requires only:
  1. a new class implementing `AIProvider` in `services/ai/providers/`, and
  2. one `registry.register(...)` line below.
The four-agent pipeline needs no changes.

Uses the shared `services.registry.Registry` (same mechanism as detectors and
extractors); like detectors, an unknown provider fails loudly (no fallback).
"""

from __future__ import annotations

from services import config
from services.ai.provider import AIProvider
from services.ai.providers.anthropic_provider import AnthropicProvider
from services.ai.providers.gemini_provider import GeminiProvider
from services.ai.providers.mock_provider import MockProvider
from services.ai.providers.router_provider import RouterProvider
from services.registry import Registry

# Re-exported for backward compatibility; the canonical value lives in config.
DEFAULT_PROVIDER = config.DEFAULT_PROVIDER

# The single place a new provider is wired in.
_registry: Registry[AIProvider] = Registry("provider")
_registry.register("mock", MockProvider)
_registry.register("anthropic", AnthropicProvider)
_registry.register("gemini", GeminiProvider)
# Sprint 17A — the router selects a delegate provider per task (see RouterProvider).
_registry.register("router", RouterProvider)


def supported_providers() -> list[str]:
    return _registry.available()


def get_provider(name: str | None = None) -> AIProvider:
    """Resolve a provider by explicit name, else the AI_PROVIDER env, else mock.

    Raises ValueError with a clear message for any unsupported value, so a
    misconfigured AI_PROVIDER fails loudly instead of silently degrading.
    """
    return _registry.create(config.resolved_provider(name))
