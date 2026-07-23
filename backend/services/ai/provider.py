"""AI provider abstraction (Sprint 1).

The rest of the application talks to LLMs exclusively through the `AIProvider`
interface and never learns whether it is speaking to Anthropic, Gemini, or the
mock. Provider-specific plumbing (HTTP, SDKs, auth, image encoding, model names)
lives entirely inside the concrete provider classes in `services/ai/providers/`.

Message content is provider-neutral: a caller passes either a plain string (text
prompt) or a list of neutral content parts, and each provider translates those
parts into its own wire format inside `send_messages`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypedDict, Union


class TextPart(TypedDict):
    type: str  # "text"
    text: str


class ImagePart(TypedDict):
    type: str  # "image"
    path: str


ContentPart = Union[TextPart, ImagePart]
# What agents pass to `send_messages`: a bare prompt or ordered multimodal parts.
MessageContent = Union[str, list[ContentPart]]


def text_part(text: str) -> TextPart:
    return {"type": "text", "text": text}


def image_part(path: str | Path) -> ImagePart:
    return {"type": "image", "path": str(path)}


def normalize_content(user_content: MessageContent) -> list[ContentPart]:
    """Coerce the neutral content into an ordered list of parts.

    A plain string becomes a single text part; a list is returned unchanged.
    This is the one place the two accepted shapes are reconciled, so every
    provider consumes the same normalized structure.
    """
    if isinstance(user_content, str):
        return [text_part(user_content)]
    return list(user_content)


class AIProvider(ABC):
    """Abstract LLM provider. Concrete providers own all vendor specifics."""

    @abstractmethod
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
        """Send one system+user turn and return the model's raw text reply.

        `user_content` is provider-neutral (see `MessageContent`). The returned
        string is validated by the caller against a Pydantic model, so providers
        must not parse or reshape it.

        `response_schema` (Sprint 16B) is an optional JSON Schema describing the
        expected reply. Providers use it to request provider-native structured
        output — Gemini JSON mode + schema, Anthropic `output_config.format` when
        enabled — so the reply is guaranteed-parseable JSON. Providers that cannot
        honor it simply ignore it (the JSON-only prompt + caller-side validation +
        retry still apply).

        `model` (Sprint 17B) is an optional per-call model override. When None a
        provider uses its own configured model (AI_MODEL/GEMINI_MODEL env or its
        built-in default), so single-provider behavior is unchanged; when set it is
        the concrete model id to call. The value is provider-neutral in the same
        way `temperature` is — a plain string the provider interprets. Providers
        with no notion of a model (e.g. the mock) accept and ignore it.
        """

    @abstractmethod
    def supports_vision(self) -> bool:
        """Whether this provider can consume image parts."""

    @abstractmethod
    def provider_name(self) -> str:
        """Stable identifier (e.g. "anthropic", "gemini", "mock")."""

    def model_name(self) -> str:
        """Resolved model id for diagnostics (Sprint 16D).

        Real providers override this to report the concrete model they will call;
        the default (the provider name) keeps mock/bench/test providers working
        without changes.
        """
        return self.provider_name()

    def route(self, task: str | None = None) -> "AIProvider":
        """Select the concrete provider to use for `task` (Sprint 17A).

        The default returns ``self`` — a single provider is used for every task, so
        the seam is a no-op. Only `RouterProvider` overrides this to pick a delegate
        per task, keeping routing entirely out of the `send_messages` contract: no
        other provider (and no sport code) ever learns routing happened.
        """
        return self

    @property
    def is_mock(self) -> bool:
        """True only for the mock demo provider.

        The four-agent pipeline uses this to choose the canned demo path instead
        of issuing real model calls. Real providers inherit the default (False)
        and never need to know about the demo path.
        """
        return False
