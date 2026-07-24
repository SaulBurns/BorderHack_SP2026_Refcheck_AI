"""Sprint 17B — per-agent providers AND models.

Sprint 17A let each pipeline stage pick its own *provider*. Sprint 17B extends
that so each stage also picks its own *model*:

    perception   → PERCEPTION_PROVIDER  + PERCEPTION_MODEL
    adjudication → ADJUDICATOR_PROVIDER + ADJUDICATOR_MODEL

These cover the resolver precedence (new vars over the legacy ROUTER_* vars),
the per-task model binding through the `route()` seam, backward compatibility,
and an end-to-end mixed-provider/mixed-model pipeline that captures the exact
model string each stage sent.
"""

import os
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import services.ai_analyzer as ai
from services import config
from services.ai import factory
from services.ai.provider import AIProvider
from services.ai.providers.router_provider import RouterProvider
from services.detectors.detection_models import DetectorResult

_PER_AGENT_ENVS = (
    "PERCEPTION_PROVIDER",
    "PERCEPTION_MODEL",
    "ADJUDICATOR_PROVIDER",
    "ADJUDICATOR_MODEL",
    "ROUTER_DEFAULT_PROVIDER",
    "ROUTER_PERCEPTION_PROVIDER",
    "ROUTER_ADJUDICATION_PROVIDER",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for env in _PER_AGENT_ENVS:
        monkeypatch.delenv(env, raising=False)


# ---------------------------------------------------------------------------
# Model resolver
# ---------------------------------------------------------------------------

def test_router_model_for_defaults_to_none():
    # No per-task model set → provider decides (its own env/default).
    assert config.router_model_for("perception") is None
    assert config.router_model_for("adjudication") is None
    assert config.router_model_for(None) is None


def test_router_model_for_per_task_env(monkeypatch):
    monkeypatch.setenv("PERCEPTION_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("ADJUDICATOR_MODEL", "claude-sonnet-4-5")
    assert config.router_model_for("perception") == "gemini-2.5-flash"
    assert config.router_model_for("adjudication") == "claude-sonnet-4-5"


def test_router_model_for_preserves_case(monkeypatch):
    # Model ids are case-sensitive — never lowercased like provider keys.
    monkeypatch.setenv("PERCEPTION_MODEL", "Gemini-2.5-Flash")
    assert config.router_model_for("perception") == "Gemini-2.5-Flash"


# ---------------------------------------------------------------------------
# Provider resolver precedence (new vars win over legacy ROUTER_* vars)
# ---------------------------------------------------------------------------

def test_new_provider_env_takes_precedence_over_legacy(monkeypatch):
    monkeypatch.setenv("PERCEPTION_PROVIDER", "gemini")
    monkeypatch.setenv("ROUTER_PERCEPTION_PROVIDER", "mock")
    assert config.router_provider_for("perception") == "gemini"


def test_legacy_provider_env_still_works(monkeypatch):
    # Backward compatibility: Sprint 17A configs keep working.
    monkeypatch.setenv("ROUTER_PERCEPTION_PROVIDER", "gemini")
    monkeypatch.setenv("ROUTER_ADJUDICATION_PROVIDER", "mock")
    assert config.router_provider_for("perception") == "gemini"
    assert config.router_provider_for("adjudication") == "mock"


def test_new_provider_env_alone(monkeypatch):
    monkeypatch.setenv("PERCEPTION_PROVIDER", "mock")
    monkeypatch.setenv("ADJUDICATOR_PROVIDER", "anthropic")
    assert config.router_provider_for("perception") == "mock"
    assert config.router_provider_for("adjudication") == "anthropic"


# ---------------------------------------------------------------------------
# route() binds the per-task model to the delegate
# ---------------------------------------------------------------------------

def test_route_binds_model_but_keeps_real_provider_name(monkeypatch):
    monkeypatch.setenv("PERCEPTION_PROVIDER", "mock")
    monkeypatch.setenv("PERCEPTION_MODEL", "custom-perception-model")
    routed = RouterProvider().route("perception")
    # provider_name stays the real delegate (diagnostics never say "router").
    assert routed.provider_name() == "mock"
    # model_name reflects the per-task override.
    assert routed.model_name() == "custom-perception-model"


def test_route_without_model_returns_bare_delegate(monkeypatch):
    # No model override → unchanged Sprint 17A behavior (bare delegate).
    monkeypatch.setenv("PERCEPTION_PROVIDER", "mock")
    routed = RouterProvider().route("perception")
    assert routed.provider_name() == "mock"
    assert routed.model_name() == "mock"  # delegate's own default


def test_describe_routing_includes_provider_and_model(monkeypatch):
    monkeypatch.setenv("PERCEPTION_PROVIDER", "gemini")
    monkeypatch.setenv("PERCEPTION_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("ADJUDICATOR_PROVIDER", "anthropic")
    monkeypatch.setenv("ADJUDICATOR_MODEL", "claude-sonnet-4-5")
    assert RouterProvider().describe_routing() == {
        "perception": {"provider": "gemini", "model": "gemini-2.5-flash"},
        "adjudication": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
    }


def test_describe_routing_model_none_when_unset(monkeypatch):
    monkeypatch.setenv("PERCEPTION_PROVIDER", "mock")
    routing = RouterProvider().describe_routing()
    assert routing["perception"] == {"provider": "mock", "model": None}


# ---------------------------------------------------------------------------
# Providers honor a per-call model override
# ---------------------------------------------------------------------------

def test_anthropic_send_messages_uses_model_override(monkeypatch):
    from services.ai.providers.anthropic_provider import AnthropicProvider

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_MODEL", "env-default-model")
    captured = {}

    def _fake_post(url, headers, payload):
        captured["model"] = payload["model"]
        return {"content": [{"type": "text", "text": "{}"}]}

    monkeypatch.setattr(AnthropicProvider, "_post_json", staticmethod(_fake_post))
    AnthropicProvider().send_messages(
        system_prompt="s", user_content="u", temperature=0.0, model="override-model"
    )
    assert captured["model"] == "override-model"


def test_anthropic_send_messages_falls_back_to_env_when_no_override(monkeypatch):
    from services.ai.providers.anthropic_provider import AnthropicProvider

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_MODEL", "env-default-model")
    captured = {}

    def _fake_post(url, headers, payload):
        captured["model"] = payload["model"]
        return {"content": [{"type": "text", "text": "{}"}]}

    monkeypatch.setattr(AnthropicProvider, "_post_json", staticmethod(_fake_post))
    AnthropicProvider().send_messages(system_prompt="s", user_content="u", temperature=0.0)
    assert captured["model"] == "env-default-model"


# ---------------------------------------------------------------------------
# End-to-end: mixed providers AND mixed models through the real pipeline
# ---------------------------------------------------------------------------

class _CapturingProvider(AIProvider):
    """Records the model string each `send_messages` call receives."""

    name = "fake"
    reply = "{}"
    models: list = []
    _lock = threading.Lock()

    def provider_name(self) -> str:
        return self.name

    def model_name(self) -> str:
        return f"{self.name}-default"

    def supports_vision(self) -> bool:
        return True

    def send_messages(self, *, model=None, **_kwargs) -> str:
        with type(self)._lock:
            type(self).models.append(model)
        return self.reply


class _PerceptionFake(_CapturingProvider):
    name = "perception_fake"
    reply = '{"event_type": "unclear", "summary": "routed", "sport": "basketball"}'
    models: list = []
    _lock = threading.Lock()


class _AdjudicationFake(_CapturingProvider):
    name = "adjudication_fake"
    reply = '{"verdict": "inconclusive", "confidence": 0.5, "reasoning": "routed"}'
    models: list = []
    _lock = threading.Lock()


@pytest.fixture
def routed_fakes(monkeypatch):
    _PerceptionFake.models = []
    _AdjudicationFake.models = []
    factory._registry.register("perception_fake", _PerceptionFake)
    factory._registry.register("adjudication_fake", _AdjudicationFake)
    monkeypatch.setenv("AI_PROVIDER", "router")
    monkeypatch.setenv("PERCEPTION_PROVIDER", "perception_fake")
    monkeypatch.setenv("PERCEPTION_MODEL", "gemini-flash-xyz")
    monkeypatch.setenv("ADJUDICATOR_PROVIDER", "adjudication_fake")
    monkeypatch.setenv("ADJUDICATOR_MODEL", "claude-sonnet-xyz")
    ai._reset_provider_cache()
    try:
        yield
    finally:
        factory._registry._items.pop("perception_fake", None)
        factory._registry._items.pop("adjudication_fake", None)
        ai._reset_provider_cache()


def test_pipeline_sends_each_task_its_configured_model(routed_fakes, monkeypatch):
    class _FakeDetector:
        name = "fake"

        def detect(self, frames, sport, original_call):
            return DetectorResult(
                perception=ai._perception_agent(frames, original_call, sport), detections=None
            )

    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    ai._run_four_agent_pipeline(
        frame_paths=[Path("f.jpg")], file=MagicMock(), sport="basketball",
        level_of_play="", league="", original_call="", referee_name="", video_metadata=None,
    )
    # Perception ran once with its model; adjudication ran twice with its model.
    assert _PerceptionFake.models == ["gemini-flash-xyz"]
    assert _AdjudicationFake.models == ["claude-sonnet-xyz", "claude-sonnet-xyz"]
