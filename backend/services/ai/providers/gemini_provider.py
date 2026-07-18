"""Gemini provider — Google GenAI SDK behind the shared AIProvider interface.

Exposes the exact same `send_messages` contract as Anthropic: same system prompt,
temperature and max-token semantics, provider-neutral text + image inputs, and a
raw text reply that the shared JSON extraction in `ai_analyzer` parses. No
pipeline logic is duplicated here.

The `google-genai` SDK is an optional dependency, imported lazily so the app runs
without it unless AI_PROVIDER=gemini is actually selected and used.
"""

from __future__ import annotations

import os
from pathlib import Path

from services import config
from services.ai.provider import AIProvider, MessageContent, normalize_content

# Re-exported for backward compatibility; canonical default lives in config.
DEFAULT_MODEL = config.DEFAULT_GEMINI_MODEL


class GeminiProvider(AIProvider):
    """Talks to Google Gemini via the official `google-genai` SDK."""

    def provider_name(self) -> str:
        return "gemini"

    def supports_vision(self) -> bool:
        return True

    def send_messages(
        self,
        *,
        system_prompt: str,
        user_content: MessageContent,
        temperature: float,
        max_tokens: int = 1200,
    ) -> str:
        api_key = os.getenv(config.GEMINI_API_KEY_ENV)
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        genai, types = self._load_sdk()
        client = genai.Client(api_key=api_key)
        model = os.getenv(config.GEMINI_MODEL_ENV) or DEFAULT_MODEL

        response = client.models.generate_content(
            model=model,
            contents=self._parts(types, user_content),
            config=types.GenerateContentConfig(
                **self.generation_kwargs(
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=config.env_flag(config.GEMINI_JSON_MODE_ENV),
                )
            ),
        )
        return response.text or ""

    # -- request building ---------------------------------------------------

    @staticmethod
    def generation_kwargs(
        *,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
    ) -> dict:
        """Build the kwargs for `types.GenerateContentConfig` (pure — unit-testable
        without the SDK installed).

        Sprint 14 — Gemini optimization: when `json_mode` is on, request
        `application/json` responses so the reply is guaranteed parseable JSON
        (removes prose/scratchpad parse failures). Off by default because JSON mode
        precludes the private <thinking> scratchpad used for chain-of-thought
        isolation, so the two are a deliberate trade-off.
        """
        kwargs = {
            "system_instruction": system_prompt,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_mime_type"] = "application/json"
        return kwargs

    # -- content translation ------------------------------------------------

    @staticmethod
    def _parts(types, user_content: MessageContent) -> list:
        """Neutral content parts -> Gemini Part list."""
        parts = []
        for part in normalize_content(user_content):
            if part["type"] == "image":
                parts.append(
                    types.Part.from_bytes(
                        data=Path(part["path"]).read_bytes(),
                        mime_type="image/jpeg",
                    )
                )
            else:
                parts.append(types.Part.from_text(text=part["text"]))
        return parts

    @staticmethod
    def _load_sdk():
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - exercised only when selected
            raise RuntimeError(
                "The 'google-genai' package is required for AI_PROVIDER=gemini. "
                "Install it (pip install google-genai) to use the Gemini provider."
            ) from exc
        return genai, types
