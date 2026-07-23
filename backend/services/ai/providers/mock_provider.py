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
        response_schema: dict | None = None,
        model: str | None = None,
    ) -> str:
        # Deterministic, valid JSON so caller-side validation succeeds if ever
        # called. `response_schema`/`model` are accepted for interface parity and
        # ignored — the mock has no real model to select.
        return json.dumps(
            {
                "verdict": "inconclusive",
                "confidence": 0.5,
                "reasoning": "Mock provider response.",
            }
        )
