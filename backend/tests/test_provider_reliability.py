"""Sprint 16D — provider-communication reliability.

Failure simulations for the transport retry layer: classification, exponential
backoff, retry-only-transient policy, enriched diagnostics, provider-comms health,
and the Anthropic HTTP-error mapping + `_send_messages` integration.
"""

import io
import os
import sys
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import services.ai_analyzer as ai
from services.ai.errors import (
    PermanentProviderError,
    TransientProviderError,
    classify_http_status,
    is_retryable_status,
)
from services.ai.providers.anthropic_provider import API_URL, AnthropicProvider
from services.ai.reliability import (
    RetryPolicy,
    call_with_retry,
    provider_health,
    reset_provider_health,
)

_ZERO_CLOCK = lambda: 0.0  # noqa: E731 — deterministic latency in tests


def _policy(**kw):
    base = dict(max_retries=2, base_delay=0.5, max_delay=8.0, jitter=0.0)
    base.update(kw)
    return RetryPolicy(**base)


def _raise(exc):
    def fn():
        raise exc
    return fn


# ---------------------------------------------------------------------------
# Status classification — transient vs permanent
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", [408, 409, 429, 500, 502, 503, 504, 529])
def test_transient_statuses(status):
    assert is_retryable_status(status)
    assert isinstance(classify_http_status(status, "x"), TransientProviderError)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_permanent_statuses(status):
    assert not is_retryable_status(status)
    assert isinstance(classify_http_status(status, "x"), PermanentProviderError)


# ---------------------------------------------------------------------------
# Backoff schedule (pure)
# ---------------------------------------------------------------------------

def test_backoff_is_exponential_and_capped():
    p = _policy(max_retries=5, base_delay=1.0, max_delay=4.0, jitter=0.0)
    assert [p.delay_for(i, 0.0) for i in range(4)] == [1.0, 2.0, 4.0, 4.0]


def test_backoff_jitter_is_bounded():
    p = _policy(base_delay=1.0, jitter=0.1)
    assert p.delay_for(0, 0.0) == 1.0        # rand=0 → no jitter
    assert p.delay_for(0, 1.0) == pytest.approx(1.1)  # rand=1 → full jitter fraction


# ---------------------------------------------------------------------------
# call_with_retry — retry ONLY transient
# ---------------------------------------------------------------------------

def test_retries_transient_then_succeeds():
    reset_provider_health()
    calls = {"n": 0}
    sleeps: list[float] = []

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TransientProviderError("blip", provider="anthropic", status=503)
        return "ok"

    out = call_with_retry(fn, provider="anthropic", model="m", policy=_policy(),
                          sleep=sleeps.append, monotonic=_ZERO_CLOCK)
    assert out == "ok"
    assert calls["n"] == 3
    assert sleeps == [0.5, 1.0]  # base*2^0, base*2^1 (jitter=0)


def test_permanent_error_is_not_retried():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise PermanentProviderError("bad request", provider="anthropic", status=400)

    with pytest.raises(PermanentProviderError):
        call_with_retry(fn, provider="anthropic", model="m", policy=_policy(),
                        sleep=lambda _s: None, monotonic=_ZERO_CLOCK)
    assert calls["n"] == 1


def test_unexpected_error_is_not_retried():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise ValueError("not a provider error")

    with pytest.raises(ValueError):
        call_with_retry(fn, provider="anthropic", model="m", policy=_policy(),
                        sleep=lambda _s: None, monotonic=_ZERO_CLOCK)
    assert calls["n"] == 1


def test_exhaustion_raises_enriched_diagnostics():
    reset_provider_health()
    with pytest.raises(TransientProviderError) as exc:
        call_with_retry(
            _raise(TransientProviderError("rate limited", provider="anthropic", status=429)),
            provider="anthropic", model="claude-x", policy=_policy(),
            sleep=lambda _s: None, monotonic=_ZERO_CLOCK,
        )
    msg = str(exc.value)
    assert "anthropic" in msg and "claude-x" in msg
    assert "3 attempt" in msg and "ms" in msg  # provider, model, retry count, latency


# ---------------------------------------------------------------------------
# Provider-comms health
# ---------------------------------------------------------------------------

def test_health_records_success_then_failure():
    reset_provider_health()
    call_with_retry(lambda: "ok", provider="anthropic", model="m", policy=_policy(),
                    sleep=lambda _s: None, monotonic=_ZERO_CLOCK)
    h = provider_health()
    assert h["ok"] is True and h["calls"] == 1 and h["last_outcome"] == "success"

    with pytest.raises(TransientProviderError):
        call_with_retry(
            _raise(TransientProviderError("down", provider="anthropic", status=500)),
            provider="anthropic", model="m", policy=_policy(),
            sleep=lambda _s: None, monotonic=_ZERO_CLOCK,
        )
    h = provider_health()
    assert h["ok"] is False
    assert h["failures"] == 1
    assert h["last_outcome"] == "transient_exhausted"
    assert h["last_provider"] == "anthropic" and h["last_attempts"] == 3
    assert h["retries"] == 2  # from the 3-attempt failed call


def test_readiness_includes_provider_comms(monkeypatch):
    reset_provider_health()
    monkeypatch.setenv("AI_PROVIDER", "mock")
    from services import health
    report = health.readiness()
    assert "provider_comms" in report["checks"]
    assert report["checks"]["provider_comms"]["ok"] is True


def test_readiness_degrades_after_provider_failure(monkeypatch):
    reset_provider_health()
    with pytest.raises(TransientProviderError):
        call_with_retry(
            _raise(TransientProviderError("down", provider="anthropic", status=503)),
            provider="anthropic", model="m", policy=_policy(),
            sleep=lambda _s: None, monotonic=_ZERO_CLOCK,
        )
    monkeypatch.setenv("AI_PROVIDER", "mock")  # provider-key check passes; comms fails
    from services import health
    report = health.readiness()
    assert report["checks"]["provider_comms"]["ok"] is False
    assert report["status"] == "degraded"


# ---------------------------------------------------------------------------
# Anthropic HTTP-error mapping (no network)
# ---------------------------------------------------------------------------

def _http_error(code):
    return urllib.error.HTTPError(API_URL, code, "err", {}, io.BytesIO(b'{"error":"boom"}'))


def test_anthropic_http_429_is_transient(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(_http_error(429)))
    with pytest.raises(TransientProviderError):
        AnthropicProvider._post_json(API_URL, {}, {"model": "m"})


def test_anthropic_http_400_is_permanent(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(_http_error(400)))
    with pytest.raises(PermanentProviderError):
        AnthropicProvider._post_json(API_URL, {}, {"model": "m"})


def test_anthropic_urlerror_is_transient(monkeypatch):
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(urllib.error.URLError("timed out")),
    )
    with pytest.raises(TransientProviderError):
        AnthropicProvider._post_json(API_URL, {}, {"model": "m"})


def test_anthropic_missing_key_is_permanent(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(PermanentProviderError):
        AnthropicProvider().send_messages(system_prompt="s", user_content="u", temperature=0.0)


# ---------------------------------------------------------------------------
# _send_messages integration (real transport-retry seam)
# ---------------------------------------------------------------------------

class _FakeProvider:
    def __init__(self, script):
        self._script = list(script)
        self.calls = 0

    def provider_name(self):
        return "anthropic"

    def model_name(self):
        return "claude-x"

    def send_messages(self, **_kwargs):
        item = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def test_send_messages_retries_transient(monkeypatch):
    reset_provider_health()
    monkeypatch.setenv("PROVIDER_BACKOFF_BASE_SECONDS", "0")  # instant real sleep(0)
    provider = _FakeProvider([TransientProviderError("blip", provider="anthropic", status=503), "reply"])
    monkeypatch.setattr(ai, "_active_provider", lambda: provider)
    out = ai._send_messages(system_prompt="s", user_content="u", temperature=0.2)
    assert out == "reply"
    assert provider.calls == 2  # one retry


def test_send_messages_permanent_not_retried(monkeypatch):
    reset_provider_health()
    provider = _FakeProvider([PermanentProviderError("bad request", provider="anthropic", status=400)])
    monkeypatch.setattr(ai, "_active_provider", lambda: provider)
    with pytest.raises(PermanentProviderError):
        ai._send_messages(system_prompt="s", user_content="u", temperature=0.2)
    assert provider.calls == 1
