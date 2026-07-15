"""Mock provider — the demo-safe, no-network provider.

The four-agent pipeline recognizes the mock provider (`is_mock`) and produces its
canned demo result directly, so `send_messages` is not exercised on the demo
path. It is still implemented so the mock satisfies the same interface as every
real provider and can be exercised in isolation.
"""

from __future__ import annotations

import json

from services.ai.provider import AIProvider, MessageContent


class MockProvider(AIProvider):
    """No-op provider used for demos and tests; never calls the network."""

    def provider_name(self) -> str:
        return "mock"

    def supports_vision(self) -> bool:
        return True

    @property
    def is_mock(self) -> bool:
        return True

    def send_messages(
        self,
        *,
        system_prompt: str,
        user_content: MessageContent,
        temperature: float,
        max_tokens: int = 1200,
    ) -> str:
        # Deterministic, valid JSON so the shared parser succeeds if ever called.
        return json.dumps(
            {
                "verdict": "inconclusive",
                "confidence": 0.5,
                "reasoning": "Mock provider response.",
            }
        )
