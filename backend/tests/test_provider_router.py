"""Sprint 17A — provider router (`AI_PROVIDER=router`).

Verifies task-based provider selection: the config resolver, the `route()` seam,
factory registration, the recursion guard, and end-to-end that the pipeline routes
the perception turn and the two adjudicator turns to their configured providers —
all without any sport code knowing which provider ran.
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
from services.ai import factory, get_provider, supported_providers
from services.ai.provider import AIProvider, MessageContent
from services.ai.providers.router_provider import RouterProvider
from services.detectors.detection_models import DetectorResult


# ---------------------------------------------------------------------------
# Config resolver
# ---------------------------------------------------------------------------

def test_router_provider_for_defaults(monkeypatch):
    for env in ("ROUTER_DEFAULT_PROVIDER", "ROUTER_PERCEPTION_PROVIDER", "ROUTER_ADJUDICATION_PROVIDER"):
        monkeypatch.delenv(env, raising=False)
    assert config.router_provider_for("perception") == "anthropic"
    assert config.router_provider_for("adjudication") == "anthropic"
    assert config.router_provider_for(None) == "anthropic"       # unknown task → default
    assert config.router_provider_for("bogus") == "anthropic"


def test_router_provider_for_per_task_env(monkeypatch):
    monkeypatch.setenv("ROUTER_PERCEPTION_PROVIDER", "gemini")
    monkeypatch.setenv("ROUTER_ADJUDICATION_PROVIDER", "mock")
    assert config.router_provider_for("perception") == "gemini"
    assert config.router_provider_for("adjudication") == "mock"


def test_router_default_provider_override(monkeypatch):
    monkeypatch.setenv("ROUTER_DEFAULT_PROVIDER", "mock")
    monkeypatch.delenv("ROUTER_PERCEPTION_PROVIDER", raising=False)
    assert config.router_provider_for("perception") == "mock"


# ---------------------------------------------------------------------------
# Factory registration
# ---------------------------------------------------------------------------

def test_factory_registers_router():
    assert "router" in supported_providers()
    assert isinstance(get_provider("router"), RouterProvider)


def test_ai_provider_router_resolves_via_env(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "router")
    assert isinstance(get_provider(), RouterProvider)


# ---------------------------------------------------------------------------
# route() seam
# ---------------------------------------------------------------------------

def test_single_provider_route_returns_self():
    mock = get_provider("mock")
    assert mock.route("perception") is mock
    assert mock.route(None) is mock  # base seam is a no-op


def test_router_route_selects_delegate_per_task(monkeypatch):
    monkeypatch.setenv("ROUTER_PERCEPTION_PROVIDER", "mock")
    monkeypatch.setenv("ROUTER_ADJUDICATION_PROVIDER", "anthropic")
    router = RouterProvider()
    assert router.route("perception").provider_name() == "mock"
    assert router.route("adjudication").provider_name() == "anthropic"


def test_router_caches_delegate(monkeypatch):
    monkeypatch.setenv("ROUTER_PERCEPTION_PROVIDER", "mock")
    router = RouterProvider()
    assert router.route("perception") is router.route("perception")


def test_router_rejects_router_delegate(monkeypatch):
    monkeypatch.setenv("ROUTER_PERCEPTION_PROVIDER", "router")
    with pytest.raises(ValueError, match="cannot route"):
        RouterProvider().route("perception")


def test_describe_routing(monkeypatch):
    # Legacy ROUTER_* provider vars still resolve; Sprint 17B reports {provider, model}
    # per task (model is None when no per-task model is pinned).
    for env in ("PERCEPTION_PROVIDER", "ADJUDICATOR_PROVIDER", "PERCEPTION_MODEL", "ADJUDICATOR_MODEL"):
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setenv("ROUTER_PERCEPTION_PROVIDER", "gemini")
    monkeypatch.setenv("ROUTER_ADJUDICATION_PROVIDER", "mock")
    assert RouterProvider().describe_routing() == {
        "perception": {"provider": "gemini", "model": None},
        "adjudication": {"provider": "mock", "model": None},
    }


# ---------------------------------------------------------------------------
# Health surfaces the routed providers
# ---------------------------------------------------------------------------

def test_health_check_provider_router(monkeypatch):
    from services import health

    monkeypatch.setenv("AI_PROVIDER", "router")
    monkeypatch.setenv("ROUTER_PERCEPTION_PROVIDER", "mock")
    monkeypatch.setenv("ROUTER_ADJUDICATION_PROVIDER", "mock")
    check = health.readiness()["checks"]["provider"]
    assert check["ok"] is True  # both routes are keyless mock
    assert "perception→mock" in check["detail"] and "adjudication→mock" in check["detail"]


# ---------------------------------------------------------------------------
# End-to-end pipeline routing
# ---------------------------------------------------------------------------

class _CapturingProvider(AIProvider):
    """Base capturing fake; subclasses set `name` and `reply` and share a counter."""

    name = "fake"
    reply = "{}"
    calls = 0
    _lock = threading.Lock()

    def provider_name(self) -> str:
        return self.name

    def model_name(self) -> str:
        return f"{self.name}-model"

    def supports_vision(self) -> bool:
        return True

    def send_messages(self, **_kwargs) -> str:
        with type(self)._lock:
            type(self).calls += 1
        return self.reply


class _PerceptionFake(_CapturingProvider):
    name = "perception_fake"
    reply = '{"event_type": "unclear", "summary": "routed to perception provider", "sport": "basketball"}'
    _lock = threading.Lock()


class _AdjudicationFake(_CapturingProvider):
    name = "adjudication_fake"
    reply = '{"verdict": "inconclusive", "confidence": 0.5, "reasoning": "routed to adjudication provider"}'
    _lock = threading.Lock()


@pytest.fixture
def routed_fakes(monkeypatch):
    _PerceptionFake.calls = 0
    _AdjudicationFake.calls = 0
    factory._registry.register("perception_fake", _PerceptionFake)
    factory._registry.register("adjudication_fake", _AdjudicationFake)
    monkeypatch.setenv("AI_PROVIDER", "router")
    monkeypatch.setenv("ROUTER_PERCEPTION_PROVIDER", "perception_fake")
    monkeypatch.setenv("ROUTER_ADJUDICATION_PROVIDER", "adjudication_fake")
    ai._reset_provider_cache()
    try:
        yield
    finally:
        factory._registry._items.pop("perception_fake", None)
        factory._registry._items.pop("adjudication_fake", None)
        ai._reset_provider_cache()


def test_pipeline_routes_each_task_to_its_provider(routed_fakes, monkeypatch):
    class _FakeDetector:
        name = "fake"
        def detect(self, frames, sport, original_call):
            # Run the real perception agent so it routes on the perception task.
            return DetectorResult(
                perception=ai._perception_agent(frames, original_call, sport), detections=None
            )

    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    result = ai._run_four_agent_pipeline(
        frame_paths=[Path("f.jpg")], file=MagicMock(), sport="basketball",
        level_of_play="", league="", original_call="", referee_name="", video_metadata=None,
    )
    assert _PerceptionFake.calls == 1     # the one perception turn
    assert _AdjudicationFake.calls == 2   # both adjudicators
    assert result["provider_used"] == "anthropic_four_agent"  # response contract unchanged


# ---------------------------------------------------------------------------
# The abstraction stays clean: no sport plugin references a provider
# ---------------------------------------------------------------------------

def test_no_sport_code_references_providers():
    sports_dir = os.path.join(os.path.dirname(__file__), "..", "sports")
    forbidden = ("send_messages", "AIProvider", "get_provider", "services.ai.providers", "AI_PROVIDER")
    offenders = []
    for root, _dirs, files in os.walk(sports_dir):
        for fname in files:
            if fname.endswith(".py"):
                path = os.path.join(root, fname)
                text = open(path, encoding="utf-8").read()
                for token in forbidden:
                    if token in text:
                        offenders.append(f"{fname}:{token}")
    assert offenders == [], f"sport code must not know about providers: {offenders}"
