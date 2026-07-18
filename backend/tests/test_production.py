"""Sprint 15 — Production readiness: auth, rate limiting, metrics, logging, health.

Pure components are unit-tested directly; the app wiring is exercised with the
FastAPI TestClient. Everything is off by default, so these tests also assert the
non-breaking baseline (no auth / no rate limiting unless configured).
"""

import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# Rate limiter (pure, injectable clock)
# ---------------------------------------------------------------------------

from services.security.rate_limit import RateLimiter, rate_limit_per_minute


def test_rate_limiter_allows_up_to_limit_then_blocks():
    limiter = RateLimiter(limit=3, window_seconds=60)
    assert [limiter.allow("ip:a", now=0.0)[0] for _ in range(3)] == [True, True, True]
    allowed, retry_after = limiter.allow("ip:a", now=0.0)
    assert allowed is False
    assert 0 < retry_after <= 60

def test_rate_limiter_window_rolls_over():
    limiter = RateLimiter(limit=1, window_seconds=60)
    assert limiter.allow("ip:a", now=0.0)[0] is True
    assert limiter.allow("ip:a", now=30.0)[0] is False
    assert limiter.allow("ip:a", now=61.0)[0] is True  # new window

def test_rate_limiter_is_per_key():
    limiter = RateLimiter(limit=1, window_seconds=60)
    assert limiter.allow("ip:a", now=0.0)[0] is True
    assert limiter.allow("ip:b", now=0.0)[0] is True  # different key, own budget

def test_rate_limiter_disabled_when_non_positive():
    limiter = RateLimiter(limit=0)
    assert all(limiter.allow("ip:a", now=0.0)[0] for _ in range(100))

def test_rate_limit_env_parsing(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
    assert rate_limit_per_minute() == 0
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "45")
    assert rate_limit_per_minute() == 45
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "nonsense")
    assert rate_limit_per_minute() == 0


# ---------------------------------------------------------------------------
# API key auth (pure)
# ---------------------------------------------------------------------------

from services.security.auth import auth_enabled, configured_api_keys, verify_api_key


def test_auth_disabled_by_default(monkeypatch):
    monkeypatch.delenv("API_KEYS", raising=False)
    monkeypatch.delenv("REFCHECK_API_KEY", raising=False)
    assert auth_enabled() is False
    # When disabled, any key (or none) verifies.
    assert verify_api_key(None) is True
    assert verify_api_key("whatever") is True

def test_auth_multi_keys_and_single(monkeypatch):
    monkeypatch.setenv("API_KEYS", "k1, k2 ,")
    monkeypatch.setenv("REFCHECK_API_KEY", "k3")
    assert configured_api_keys() == frozenset({"k1", "k2", "k3"})
    assert auth_enabled() is True

def test_auth_verifies_only_configured_keys(monkeypatch):
    monkeypatch.setenv("API_KEYS", "secret-key")
    monkeypatch.delenv("REFCHECK_API_KEY", raising=False)
    assert verify_api_key("secret-key") is True
    assert verify_api_key("wrong") is False
    assert verify_api_key(None) is False


# ---------------------------------------------------------------------------
# Metrics registry (Prometheus text)
# ---------------------------------------------------------------------------

from services.observability.metrics import MetricsRegistry


def test_metrics_counter_and_render():
    reg = MetricsRegistry()
    reg.describe("refcheck_test_total", "help text")
    reg.inc("refcheck_test_total", {"status": "200"})
    reg.inc("refcheck_test_total", {"status": "200"})
    reg.inc("refcheck_test_total", {"status": "500"})
    text = reg.render()
    assert "# TYPE refcheck_test_total counter" in text
    assert 'refcheck_test_total{status="200"} 2' in text
    assert 'refcheck_test_total{status="500"} 1' in text
    assert reg.counter_value("refcheck_test_total", {"status": "200"}) == 2

def test_metrics_summary_render():
    reg = MetricsRegistry()
    reg.observe("refcheck_dur_seconds", 0.5, {"path": "/x"})
    reg.observe("refcheck_dur_seconds", 1.5, {"path": "/x"})
    text = reg.render()
    assert 'refcheck_dur_seconds_count{path="/x"} 2' in text
    assert 'refcheck_dur_seconds_sum{path="/x"} 2' in text

def test_metrics_escapes_label_values():
    reg = MetricsRegistry()
    reg.inc("m_total", {"path": 'a"b'})
    assert 'a\\"b' in reg.render()


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------

from services.observability.logging_config import JsonLogFormatter, configure_logging


def test_json_log_formatter_emits_structured_fields():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="refcheck", level=logging.INFO, pathname="", lineno=0,
        msg="request", args=(), exc_info=None,
    )
    record.request_id = "abc123"
    record.status = 200
    line = formatter.format(record)
    parsed = json.loads(line)
    assert parsed["message"] == "request"
    assert parsed["level"] == "INFO"
    assert parsed["request_id"] == "abc123"
    assert parsed["status"] == 200

def test_configure_logging_is_idempotent_and_sets_level():
    configure_logging(level="WARNING", fmt="plain")
    assert logging.getLogger().level == logging.WARNING
    configure_logging(level="INFO", fmt="json")  # no error on re-call
    assert logging.getLogger().level == logging.INFO


# ---------------------------------------------------------------------------
# Health / readiness (pure)
# ---------------------------------------------------------------------------

from services import health


def test_liveness_is_backward_compatible():
    payload = health.liveness()
    # Legacy contract preserved.
    assert payload["status"] == "ok"
    assert payload["message"] == "RefCheck AI backend is running"
    # New additive fields.
    assert "version" in payload and "uptime_seconds" in payload

def test_readiness_reports_checks(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    report = health.readiness()
    assert report["status"] in {"ready", "degraded"}
    assert set(report["checks"]) == {"provider", "ffmpeg", "upload_dir"}
    # Mock provider needs no key -> provider check passes.
    assert report["checks"]["provider"]["ok"] is True

def test_readiness_flags_missing_provider_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    report = health.readiness()
    assert report["checks"]["provider"]["ok"] is False
    assert report["status"] == "degraded"


# ---------------------------------------------------------------------------
# App wiring (FastAPI TestClient)
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health_endpoint_backward_compatible(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["message"] == "RefCheck AI backend is running"
    # Every response carries a request id for tracing.
    assert resp.headers.get("X-Request-ID")

def test_ready_endpoint(client):
    resp = client.get("/api/health/ready")
    assert resp.status_code in {200, 503}
    assert resp.json()["status"] in {"ready", "degraded"}

def test_version_endpoint(client):
    body = client.get("/api/version").json()
    assert "version" in body and "environment" in body

def test_metrics_endpoint_exposes_request_counter(client):
    client.get("/api/health")
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    assert "refcheck_http_requests_total" in resp.text

def test_metrics_uses_route_template_not_raw_path(client):
    # A dynamic media path must not explode metric cardinality.
    client.get("/api/clips/does-not-exist.mp4")
    text = client.get("/api/metrics").text
    assert "/api/clips/{stored_name}" in text

def test_analyze_requires_key_when_auth_enabled(client, monkeypatch):
    monkeypatch.setenv("API_KEYS", "prod-secret")
    resp = client.post(
        "/api/analyze",
        files={"file": ("clip.mp4", b"\x00\x00\x00\x18ftypmp42", "video/mp4")},
        data={"sport": "basketball"},
    )
    assert resp.status_code == 401

def test_analyze_open_when_auth_disabled(client, monkeypatch):
    # No API_KEYS set -> auth is a no-op; the request is not rejected with 401.
    monkeypatch.delenv("API_KEYS", raising=False)
    monkeypatch.delenv("REFCHECK_API_KEY", raising=False)
    monkeypatch.setenv("AI_PROVIDER", "mock")
    resp = client.post(
        "/api/analyze",
        files={"file": ("clip.mp4", b"\x00\x00\x00\x18ftypmp42", "video/mp4")},
        data={"sport": "basketball"},
    )
    assert resp.status_code != 401
