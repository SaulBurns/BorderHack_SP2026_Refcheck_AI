"""Anthropic provider — verbatim move of the Claude Messages plumbing.

Every behavior (model default, AI_MODEL override, temperature/max_tokens pass
through, base64 image encoding, HTTP call, text extraction) is preserved exactly
as it was in `ai_analyzer.py`. No prompt, retry, or diagnostic behavior changed.
"""

from __future__ import annotations

import base64
import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from services import config
from services.ai.errors import PermanentProviderError, TransientProviderError, classify_http_status
from services.ai.provider import AIProvider, MessageContent, normalize_content

try:
    import certifi
except ImportError:  # pragma: no cover - certifi is a soft dependency
    certifi = None

# Re-exported for backward compatibility; canonical default lives in config.
DEFAULT_MODEL = config.DEFAULT_ANTHROPIC_MODEL
API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(AIProvider):
    """Talks to the Anthropic Messages API over HTTPS (stdlib only)."""

    def provider_name(self) -> str:
        return "anthropic"

    def model_name(self) -> str:
        return os.getenv(config.AI_MODEL_ENV) or DEFAULT_MODEL

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
        model: str | None = None,
    ) -> str:
        api_key = os.getenv(config.ANTHROPIC_API_KEY_ENV)
        if not api_key:
            # Auth/config error — never retry.
            raise PermanentProviderError("ANTHROPIC_API_KEY is not set", provider="anthropic")

        # Sprint 17B — a per-call `model` override wins over the AI_MODEL env/default.
        model = model or os.getenv(config.AI_MODEL_ENV) or DEFAULT_MODEL
        payload = self.build_payload(
            model=model,
            system_prompt=system_prompt,
            blocks=self._blocks(user_content),
            temperature=temperature,
            max_tokens=max_tokens,
            prompt_cache=config.env_flag(config.ANTHROPIC_PROMPT_CACHE_ENV),
            response_schema=response_schema,
            structured_output=config.env_flag(config.ANTHROPIC_STRUCTURED_OUTPUT_ENV),
        )
        response = self._post_json(
            API_URL,
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            payload,
        )
        return self._text_from_response(response)

    # -- request building ---------------------------------------------------

    @staticmethod
    def build_payload(
        *,
        model: str,
        system_prompt: str,
        blocks: list[dict],
        temperature: float,
        max_tokens: int,
        prompt_cache: bool = False,
        response_schema: dict | None = None,
        structured_output: bool = False,
    ) -> dict:
        """Build the Anthropic Messages request body (pure — unit-testable).

        Sprint 14 — Claude optimization: when `prompt_cache` is on, the large,
        reused system prompt (identical across both adjudicators and repeat
        analyses) is sent as a cache-controlled block so Anthropic serves it from
        cache, cutting input cost and latency. Default off, so the request is
        byte-for-byte the legacy payload unless explicitly enabled.

        Sprint 16B — structured output: when `structured_output` is on **and** a
        `response_schema` is supplied, the reply is constrained to that JSON Schema
        via `output_config.format` (native structured outputs). Default off because
        the default model (claude-sonnet-4-5) does not guarantee support — the
        pipeline then relies on the JSON-only prompt + caller-side validation +
        retry ("robust JSON mode"). Both flags off = byte-for-byte the legacy body.
        """
        system: object = system_prompt
        if prompt_cache:
            system = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        payload: dict = {
            "model": model,
            "system": system,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": blocks}],
        }
        if structured_output and response_schema is not None:
            payload["output_config"] = {
                "format": {
                    "type": "json_schema",
                    "name": response_schema.get("title", "response"),
                    "schema": response_schema,
                }
            }
        return payload

    # -- content translation ------------------------------------------------

    @staticmethod
    def _blocks(user_content: MessageContent) -> list[dict]:
        """Neutral content parts -> Anthropic message blocks."""
        blocks: list[dict] = []
        for part in normalize_content(user_content):
            if part["type"] == "image":
                data = base64.b64encode(Path(part["path"]).read_bytes()).decode("utf-8")
                blocks.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": data,
                        },
                    }
                )
            else:
                blocks.append({"type": "text", "text": part["text"]})
        return blocks

    # -- HTTP ---------------------------------------------------------------

    @staticmethod
    def _post_json(url: str, headers: dict[str, str], payload: dict) -> dict:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        context = ssl.create_default_context(cafile=certifi.where()) if certifi else None
        timeout = config.env_float(
            config.PROVIDER_TIMEOUT_SECONDS_ENV, config.DEFAULT_PROVIDER_TIMEOUT_SECONDS
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Classify by status: 429/5xx (incl. 529) are transient and retried;
            # 400/401/403/404 and other 4xx are permanent and never retried.
            body = exc.read().decode("utf-8", errors="replace")
            raise classify_http_status(
                exc.code, f"AI provider HTTP {exc.code}: {body}", provider="anthropic"
            ) from exc
        except urllib.error.URLError as exc:
            # Network failure or timeout — transient, worth retrying.
            raise TransientProviderError(
                f"AI provider request failed: {exc.reason}", provider="anthropic"
            ) from exc

    @staticmethod
    def _text_from_response(response: dict) -> str:
        return "".join(
            block.get("text", "")
            for block in response.get("content", [])
            if block.get("type") == "text"
        )
