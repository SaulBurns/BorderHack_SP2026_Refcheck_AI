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
        response_schema: dict | None = None,
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
                    response_schema=response_schema,
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
        response_schema: dict | None = None,
    ) -> dict:
        """Build the kwargs for `types.GenerateContentConfig` (pure — unit-testable
        without the SDK installed).

        Sprint 16B — structured output: when a `response_schema` is supplied the
        reply is constrained to it via Gemini controlled generation —
        `response_mime_type="application/json"` + `response_schema=<schema>` — so the
        reply is guaranteed-parseable JSON matching the schema. This is Gemini's
        native JSON mode and supersedes the legacy `json_mode` flag whenever the
        pipeline validates. `json_mode` alone (no schema) still requests plain
        `application/json` for backward compatibility.
        """
        kwargs = {
            "system_instruction": system_prompt,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if response_schema is not None:
            kwargs["response_mime_type"] = "application/json"
            kwargs["response_schema"] = response_schema
        elif json_mode:
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
