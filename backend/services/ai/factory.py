"""Provider factory — selects a provider from the AI_PROVIDER env var.

Adding a future provider (OpenAI, Azure, Grok, Ollama, ...) requires only:
  1. a new class implementing `AIProvider` in `services/ai/providers/`, and
  2. one entry in `_PROVIDERS` below.
The four-agent pipeline needs no changes.
"""

from __future__ import annotations

import os

from services.ai.provider import AIProvider
from services.ai.providers.anthropic_provider import AnthropicProvider
from services.ai.providers.gemini_provider import GeminiProvider
from services.ai.providers.mock_provider import MockProvider

DEFAULT_PROVIDER = "mock"

# Registry: provider name -> factory callable. This is the single place a new
# provider is wired in.
_PROVIDERS: dict[str, type[AIProvider]] = {
    "mock": MockProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}


def supported_providers() -> list[str]:
    return sorted(_PROVIDERS)


def get_provider(name: str | None = None) -> AIProvider:
    """Resolve a provider by explicit name, else the AI_PROVIDER env, else mock.

    Raises ValueError with a clear message for any unsupported value, so a
    misconfigured AI_PROVIDER fails loudly instead of silently degrading.
    """
    key = (name or os.getenv("AI_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    provider_cls = _PROVIDERS.get(key)
    if provider_cls is None:
        raise ValueError(
            f"Unsupported AI_PROVIDER {key!r}. "
            f"Supported providers: {', '.join(supported_providers())}."
        )
    return provider_cls()
