"""Sprint 16B — structured outputs + Pydantic validation.

Covers the replacement of the regex `_extract_json` with provider-native
structured output + `model_validate_json`:

- malformed JSON, missing fields, extra fields
- retry behavior (retry ONLY on validation failure; provider errors propagate)
- the pipeline degrades to the mock fallback with a validation `fallback_reason`
- the provider request builders emit native structured-output config
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import services.ai_analyzer as ai
from services.ai_analyzer import StructuredOutputError, _send_validated
from services.ai.providers.anthropic_provider import AnthropicProvider
from services.ai.providers.gemini_provider import GeminiProvider
from services.analysis.response_models import AdjudicatorResponse, PerceptionResponse
from services.detectors.detection_models import DetectorResult

_GOOD_ADJ = '{"verdict": "fair_call", "confidence": 0.7, "reasoning": "ok"}'
_GOOD_PERCEPTION = '{"event_type": "possible_foul", "summary": "a play"}'


def _replies(monkeypatch, sequence):
    """Monkeypatch `_send_messages` to return each item of `sequence` in turn.

    A str item is returned; an Exception item is raised. Returns a call counter.
    """
    calls = {"n": 0}
    seq = list(sequence)

    def fake(*, system_prompt, user_content, temperature, max_tokens=1200, response_schema=None, task=None):
        calls["n"] += 1
        item = seq[min(calls["n"] - 1, len(seq) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(ai, "_send_messages", fake)
    return calls


# ---------------------------------------------------------------------------
# Schemas are flat (provider-friendly, no $defs)
# ---------------------------------------------------------------------------

def test_response_schemas_are_flat():
    for model in (AdjudicatorResponse, PerceptionResponse):
        schema = model.model_json_schema()
        assert "$defs" not in schema
        assert schema["type"] == "object"


# ---------------------------------------------------------------------------
# Happy path + extra fields
# ---------------------------------------------------------------------------

def test_valid_reply_validates_and_returns_dict(monkeypatch):
    _replies(monkeypatch, [_GOOD_ADJ])
    out = _send_validated(
        system_prompt="s", user_content="u", temperature=0.2, model_cls=AdjudicatorResponse
    )
    assert out["verdict"] == "fair_call"
    assert out["confidence"] == 0.7


def test_extra_fields_are_accepted_and_ignored(monkeypatch):
    _replies(monkeypatch, ['{"verdict": "bad_call", "confidence": 0.5, "reasoning": "r", "bogus": 123}'])
    out = _send_validated(
        system_prompt="s", user_content="u", temperature=0.2, model_cls=AdjudicatorResponse
    )
    assert out["verdict"] == "bad_call"
    assert "bogus" not in out  # extra="ignore" drops unknown keys


def test_perception_extra_fields_pass_through(monkeypatch):
    # PerceptionResponse is permissive (extra="allow"): the full sport-specific body
    # passes through untouched.
    _replies(monkeypatch, ['{"event_type": "x", "summary": "s", "sport_details": {"soccer": {"in_penalty_area": true}}}'])
    out = _send_validated(
        system_prompt="s", user_content="u", temperature=0.0, model_cls=PerceptionResponse
    )
    assert out["event_type"] == "x"
    assert out["sport_details"] == {"soccer": {"in_penalty_area": True}}


# ---------------------------------------------------------------------------
# Malformed JSON / missing fields → retry, then StructuredOutputError
# ---------------------------------------------------------------------------

def test_malformed_json_retries_then_raises(monkeypatch):
    calls = _replies(monkeypatch, ["this is not json"])  # always bad
    with pytest.raises(StructuredOutputError, match="validation failed"):
        _send_validated(
            system_prompt="s", user_content="u", temperature=0.2,
            model_cls=AdjudicatorResponse, retries=1,
        )
    assert calls["n"] == 2  # initial attempt + 1 retry


def test_missing_required_field_retries(monkeypatch):
    calls = _replies(monkeypatch, ['{"confidence": 0.6}'])  # missing verdict
    with pytest.raises(StructuredOutputError):
        _send_validated(
            system_prompt="s", user_content="u", temperature=0.2,
            model_cls=AdjudicatorResponse, retries=2,
        )
    assert calls["n"] == 3  # initial + 2 retries


def test_perception_missing_core_field_retries(monkeypatch):
    calls = _replies(monkeypatch, ['{"summary": "no event_type here"}'])
    with pytest.raises(StructuredOutputError):
        _send_validated(
            system_prompt="s", user_content="u", temperature=0.0,
            model_cls=PerceptionResponse, retries=1,
        )
    assert calls["n"] == 2


def test_one_bad_then_good_succeeds(monkeypatch):
    calls = _replies(monkeypatch, ["not json", _GOOD_ADJ])
    out = _send_validated(
        system_prompt="s", user_content="u", temperature=0.2,
        model_cls=AdjudicatorResponse, retries=1,
    )
    assert out["verdict"] == "fair_call"
    assert calls["n"] == 2  # exactly one retry


def test_retries_default_to_one(monkeypatch):
    monkeypatch.delenv("STRUCTURED_OUTPUT_RETRIES", raising=False)
    calls = _replies(monkeypatch, ["not json"])
    with pytest.raises(StructuredOutputError):
        _send_validated(
            system_prompt="s", user_content="u", temperature=0.2, model_cls=AdjudicatorResponse
        )
    assert calls["n"] == 2  # default: initial + 1 retry


# ---------------------------------------------------------------------------
# Retry ONLY validation failures — provider/network errors propagate untouched
# ---------------------------------------------------------------------------

def test_provider_error_is_not_retried(monkeypatch):
    calls = _replies(monkeypatch, [RuntimeError("network down")])
    with pytest.raises(RuntimeError, match="network down"):
        _send_validated(
            system_prompt="s", user_content="u", temperature=0.2,
            model_cls=AdjudicatorResponse, retries=3,
        )
    assert calls["n"] == 1  # raised immediately, no retry


# ---------------------------------------------------------------------------
# Pipeline: a validation failure degrades to the mock fallback with a reason
# ---------------------------------------------------------------------------

def test_pipeline_falls_back_to_mock_on_validation_failure(monkeypatch):
    class _FakeDetector:
        name = "fake"
        def detect(self, frames, sport, original_call):
            return DetectorResult(
                perception={"sport": sport, "event_type": "unclear", "summary": "s"},
                detections=None,
            )

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    # Adjudicator replies are unparseable → validation fails after retries.
    _replies(monkeypatch, ["never valid json"])

    result = ai._run_four_agent_pipeline(
        frame_paths=[Path("f.jpg")], file=MagicMock(), sport="basketball",
        level_of_play="", league="", original_call="", referee_name="", video_metadata=None,
    )
    assert result["provider_used"] == "mock"
    assert "validation failed" in result["fallback_reason"]


# ---------------------------------------------------------------------------
# Provider request builders emit native structured-output config
# ---------------------------------------------------------------------------

def test_anthropic_payload_adds_output_config_when_enabled():
    schema = AdjudicatorResponse.model_json_schema()
    on = AnthropicProvider.build_payload(
        model="claude-x", system_prompt="SYS", blocks=[{"type": "text", "text": "hi"}],
        temperature=0.2, max_tokens=100, response_schema=schema, structured_output=True,
    )
    fmt = on["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["schema"] == schema


def test_anthropic_payload_omits_output_config_by_default():
    schema = AdjudicatorResponse.model_json_schema()
    # Flag off (robust JSON mode) — no output_config even with a schema present.
    off = AnthropicProvider.build_payload(
        model="claude-x", system_prompt="SYS", blocks=[{"type": "text", "text": "hi"}],
        temperature=0.2, max_tokens=100, response_schema=schema, structured_output=False,
    )
    assert "output_config" not in off


def test_gemini_generation_kwargs_with_schema():
    schema = AdjudicatorResponse.model_json_schema()
    kwargs = GeminiProvider.generation_kwargs(
        system_prompt="SYS", temperature=0.3, max_tokens=200, response_schema=schema,
    )
    assert kwargs["response_mime_type"] == "application/json"
    assert kwargs["response_schema"] == schema


def test_gemini_generation_kwargs_without_schema_is_plain():
    kwargs = GeminiProvider.generation_kwargs(
        system_prompt="SYS", temperature=0.3, max_tokens=200,
    )
    assert "response_schema" not in kwargs
    assert "response_mime_type" not in kwargs
