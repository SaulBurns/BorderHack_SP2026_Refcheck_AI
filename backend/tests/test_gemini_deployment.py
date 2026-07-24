"""Sprint 17C — Gemini production readiness.

Covers the deployment-hardening seams that make `AI_PROVIDER=gemini` (and a
Gemini leg of `AI_PROVIDER=router`) safe to run in production:

- SDK availability probe (`GeminiProvider.sdk_available`)
- config: `PROVIDER_FALLBACK` + per-provider model resolution
- startup validation & config summary (`services/ai/startup.py`)
- readiness surfaces Gemini's key + SDK, and is failover-aware
- the pipeline gracefully fails over to a secondary provider before the mock
"""

import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services import config
from services.ai import startup
from services.ai.errors import PermanentProviderError
from services.ai.provider import AIProvider
from services.ai.providers.gemini_provider import GeminiProvider

_AI_ENVS = (
    "AI_PROVIDER", "AI_MODEL", "GEMINI_MODEL", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
    "PROVIDER_FALLBACK", "PERCEPTION_PROVIDER", "ADJUDICATOR_PROVIDER",
    "PERCEPTION_MODEL", "ADJUDICATOR_MODEL",
    "ROUTER_PERCEPTION_PROVIDER", "ROUTER_ADJUDICATION_PROVIDER", "ROUTER_DEFAULT_PROVIDER",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for env in _AI_ENVS:
        monkeypatch.delenv(env, raising=False)


# ---------------------------------------------------------------------------
# SDK availability probe
# ---------------------------------------------------------------------------

def test_sdk_available_true_when_spec_found(monkeypatch):
    monkeypatch.setattr(startup.importlib.util, "find_spec", lambda name: object())
    assert GeminiProvider.sdk_available() is True


def test_sdk_available_false_when_spec_missing(monkeypatch):
    monkeypatch.setattr(startup.importlib.util, "find_spec", lambda name: None)
    assert GeminiProvider.sdk_available() is False


def test_sdk_available_false_on_import_error(monkeypatch):
    def _boom(name):
        raise ModuleNotFoundError("no google")
    monkeypatch.setattr(startup.importlib.util, "find_spec", _boom)
    assert GeminiProvider.sdk_available() is False


# ---------------------------------------------------------------------------
# config: fallback provider + model resolution
# ---------------------------------------------------------------------------

def test_fallback_provider_defaults_none():
    assert config.fallback_provider() is None


def test_fallback_provider_env(monkeypatch):
    monkeypatch.setenv("PROVIDER_FALLBACK", " Anthropic ")
    assert config.fallback_provider() == "anthropic"


def test_resolved_model_for_provider_defaults():
    assert config.resolved_model_for_provider("anthropic") == config.DEFAULT_ANTHROPIC_MODEL
    assert config.resolved_model_for_provider("gemini") == config.DEFAULT_GEMINI_MODEL
    assert config.resolved_model_for_provider("mock") is None


def test_resolved_model_for_provider_env_override(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3-pro")
    monkeypatch.setenv("AI_MODEL", "claude-opus-4-8")
    assert config.resolved_model_for_provider("gemini") == "gemini-3-pro"
    assert config.resolved_model_for_provider("anthropic") == "claude-opus-4-8"


# ---------------------------------------------------------------------------
# startup.provider_status
# ---------------------------------------------------------------------------

def test_provider_status_mock():
    ok, detail = startup.provider_status("mock")
    assert ok is True


def test_provider_status_anthropic_missing_key():
    ok, detail = startup.provider_status("anthropic")
    assert ok is False and "key" in detail.lower()


def test_provider_status_anthropic_ok(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")
    assert startup.provider_status("anthropic")[0] is True


def test_provider_status_gemini_missing_sdk(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g-x")
    monkeypatch.setattr(GeminiProvider, "sdk_available", staticmethod(lambda: False))
    ok, detail = startup.provider_status("gemini")
    assert ok is False and "sdk" in detail.lower()


def test_provider_status_gemini_ok(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g-x")
    monkeypatch.setattr(GeminiProvider, "sdk_available", staticmethod(lambda: True))
    assert startup.provider_status("gemini")[0] is True


def test_provider_status_gemini_missing_key(monkeypatch):
    monkeypatch.setattr(GeminiProvider, "sdk_available", staticmethod(lambda: True))
    ok, detail = startup.provider_status("gemini")
    assert ok is False and "key" in detail.lower()


def test_provider_status_unknown():
    assert startup.provider_status("grok")[0] is False


# ---------------------------------------------------------------------------
# startup.validate_ai_config
# ---------------------------------------------------------------------------

def test_validate_ai_config_mock_clean(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    assert startup.validate_ai_config() == []


def test_validate_ai_config_anthropic_missing_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    warnings = startup.validate_ai_config()
    assert any("anthropic" in w.lower() for w in warnings)


def test_validate_ai_config_gemini_missing_sdk(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-x")
    monkeypatch.setattr(GeminiProvider, "sdk_available", staticmethod(lambda: False))
    warnings = startup.validate_ai_config()
    assert any("sdk" in w.lower() for w in warnings)


def test_validate_ai_config_unsupported_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "grok")
    warnings = startup.validate_ai_config()
    assert any("grok" in w.lower() for w in warnings)


def test_validate_ai_config_router_validates_each_route(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "router")
    monkeypatch.setenv("PERCEPTION_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-x")
    monkeypatch.setattr(GeminiProvider, "sdk_available", staticmethod(lambda: False))
    monkeypatch.setenv("ADJUDICATOR_PROVIDER", "mock")
    warnings = startup.validate_ai_config()
    assert any("gemini" in w.lower() for w in warnings)


def test_validate_ai_config_fallback_unsupported(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("PROVIDER_FALLBACK", "grok")
    warnings = startup.validate_ai_config()
    assert any("grok" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# startup.ai_config_summary
# ---------------------------------------------------------------------------

def test_ai_config_summary_gemini(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("PROVIDER_FALLBACK", "anthropic")
    monkeypatch.setattr(GeminiProvider, "sdk_available", staticmethod(lambda: True))
    summary = startup.ai_config_summary()
    assert summary["provider"] == "gemini"
    assert summary["model"] == config.DEFAULT_GEMINI_MODEL
    assert summary["fallback"] == "anthropic"
    assert summary["gemini_sdk_available"] is True


# ---------------------------------------------------------------------------
# readiness: Gemini key + SDK, failover-aware
# ---------------------------------------------------------------------------

def test_readiness_gemini_missing_sdk_degrades(monkeypatch):
    from services import health
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-x")
    monkeypatch.setattr(GeminiProvider, "sdk_available", staticmethod(lambda: False))
    report = health.readiness()
    assert report["checks"]["provider"]["ok"] is False


def test_readiness_failover_available_keeps_provider_ok(monkeypatch):
    from services import health
    # Primary anthropic has no key, but a keyless mock fallback covers it.
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("PROVIDER_FALLBACK", "mock")
    report = health.readiness()
    assert report["checks"]["provider"]["ok"] is True
    assert "failover" in report["checks"]["provider"]["detail"].lower()


def test_readiness_checks_keys_unchanged(monkeypatch):
    from services import health
    monkeypatch.setenv("AI_PROVIDER", "mock")
    report = health.readiness()
    # The public readiness contract (existing tests) must not gain/lose check keys.
    assert set(report["checks"]) == {"provider", "provider_comms", "ffmpeg", "upload_dir"}


# ---------------------------------------------------------------------------
# pipeline: graceful failover in _send_messages
# ---------------------------------------------------------------------------

class _Fail(AIProvider):
    def provider_name(self): return "primary_fail"
    def model_name(self): return "m1"
    def supports_vision(self): return True
    def send_messages(self, **_kw):
        raise PermanentProviderError("boom", provider="primary_fail")


class _OK(AIProvider):
    calls = 0
    def provider_name(self): return "secondary_ok"
    def model_name(self): return "m2"
    def supports_vision(self): return True
    def send_messages(self, **_kw):
        type(self).calls += 1
        return "secondary-reply"


def test_send_messages_fails_over_to_fallback(monkeypatch):
    import services.ai_analyzer as ai
    _OK.calls = 0
    monkeypatch.setattr(ai, "_active_provider", lambda: _Fail())
    monkeypatch.setattr(ai, "get_provider", lambda name=None: _OK())
    monkeypatch.setenv("PROVIDER_FALLBACK", "secondary_ok")
    out = ai._send_messages(system_prompt="s", user_content="u", temperature=0.0)
    assert out == "secondary-reply"
    assert _OK.calls == 1


def test_send_messages_no_fallback_propagates(monkeypatch):
    import services.ai_analyzer as ai
    monkeypatch.setattr(ai, "_active_provider", lambda: _Fail())
    monkeypatch.delenv("PROVIDER_FALLBACK", raising=False)
    with pytest.raises(PermanentProviderError):
        ai._send_messages(system_prompt="s", user_content="u", temperature=0.0)
