import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import services.ai_analyzer as ai
import scripts.demo_analyze as demo
from services.ai_analyzer import _build_response
from scripts.demo_analyze import (
    format_report,
    main,
    preflight,
    preflight_blockers,
    run_demo,
)


def _check(checks, name):
    return next(c for c in checks if c.name == name)


def _fake_video(tmp_path):
    video = tmp_path / "NBA_GAME.mp4"
    video.write_bytes(b"\x00\x00\x00\x1cftypmp42")
    return video


# ---------------------------------------------------------------------------
# Fallback reason is now surfaced in diagnostics (no more silent mock degrade)
# ---------------------------------------------------------------------------

def test_mock_fallback_reason_is_visible(monkeypatch, tmp_path):
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    resp = run_demo(str(_fake_video(tmp_path)), provider="mock")
    diag = resp["diagnostics"]
    assert diag["provider_used"] == "mock"
    assert diag["detector"] == "mock"
    assert diag["fallback_reason"] == "AI_PROVIDER is set to mock."
    # verdict + cited rule still produced
    assert resp["verdict"]["verdict"] in ("fair_call", "bad_call", "inconclusive")
    assert resp["verdict"]["cited_rule"]["rule_id"]

def test_real_anthropic_path_has_no_fallback_reason():
    agent_result = {
        "provider_used": "anthropic_four_agent",
        "detector": "claude_vision",
        "retrieval_query": "q",
        "retrieved_rules": [],
        "perception": {"sport": "basketball", "event_type": "unclear"},
        "adjudicator_a": {"verdict": "fair_call", "confidence": 0.7, "primary_rule_id": None, "reasoning": "r", "flags": []},
        "adjudicator_b": {"verdict": "fair_call", "confidence": 0.7, "primary_rule_id": None, "reasoning": "r", "flags": []},
    }
    resp = _build_response(
        agent_result=agent_result,
        clip_id="x",
        frame_paths=[],
        video_metadata=None,
        processing_time_seconds=1.0,
        sport="basketball",
    )
    assert resp["diagnostics"]["fallback_reason"] is None
    assert resp["diagnostics"]["detector"] == "claude_vision"


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

def test_run_demo_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        run_demo("/no/such/clip.mp4", provider="mock")

def test_run_demo_restores_env(monkeypatch, tmp_path):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("DETECTOR", raising=False)
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    run_demo(str(_fake_video(tmp_path)), provider="mock", detector="hybrid")
    assert os.environ.get("AI_PROVIDER") is None
    assert os.environ.get("DETECTOR") is None

def test_format_report_flags_mock_as_not_real(monkeypatch, tmp_path):
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    resp = run_demo(str(_fake_video(tmp_path)), provider="mock")
    report = format_report(resp)
    assert "WHAT ACTUALLY RAN" in report
    assert "REAL PIPELINE RAN: NO" in report
    assert ">>> FELL BACK TO MOCK <<<" in report
    assert "fallback_reason" in report

def test_format_report_flags_real_as_true():
    resp = {
        "verdict": {"verdict": "fair_call", "confidence": 0.7, "cited_rule": {"rule_id": "BLOCK_CHARGE", "section_title": "x"}, "reasoning": "r"},
        "diagnostics": {"provider_used": "anthropic_four_agent", "detector": "claude_vision", "fallback_reason": None},
    }
    assert "REAL PIPELINE RAN: YES" in format_report(resp)

def test_main_smoke(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    rc = main(["--video", str(_fake_video(tmp_path)), "--provider", "mock"])
    assert rc == 0
    assert "WHAT ACTUALLY RAN" in capsys.readouterr().out

def test_main_missing_file_returns_2(tmp_path):
    assert main(["--video", str(tmp_path / "nope.mp4"), "--provider", "mock"]) == 2


# ---------------------------------------------------------------------------
# Preflight (Part A)
# ---------------------------------------------------------------------------

def test_preflight_reports_missing_ffmpeg(monkeypatch, tmp_path):
    # ffmpeg is critical when we intend a real (anthropic) run.
    monkeypatch.setattr(demo.shutil, "which", lambda name: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    checks = preflight(video_path=str(_fake_video(tmp_path)), provider="anthropic", detector="claude_vision")
    ffmpeg = _check(checks, "ffmpeg")
    assert ffmpeg.passed is False
    assert ffmpeg.critical is True

def test_preflight_reports_missing_api_key_for_anthropic(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    checks = preflight(video_path=str(_fake_video(tmp_path)), provider="anthropic", detector="claude_vision")
    key = _check(checks, "anthropic_api_key")
    assert key.passed is False
    assert key.critical is True
    assert preflight_blockers(checks)  # a real run is impossible

def test_preflight_api_key_not_required_for_mock(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    checks = preflight(video_path=str(_fake_video(tmp_path)), provider="mock", detector="claude_vision")
    key = _check(checks, "anthropic_api_key")
    assert key.passed is True
    assert key.critical is False

def test_preflight_reports_missing_ultralytics_for_hybrid(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(demo, "_module_available", lambda name: name != "ultralytics")
    checks = preflight(video_path=str(_fake_video(tmp_path)), provider="anthropic", detector="hybrid")
    ultra = _check(checks, "ultralytics")
    assert ultra.passed is False
    assert ultra.critical is True

def test_preflight_ultralytics_not_required_for_claude_vision(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(demo, "_module_available", lambda name: False)
    checks = preflight(video_path=str(_fake_video(tmp_path)), provider="anthropic", detector="claude_vision")
    ultra = _check(checks, "ultralytics")
    assert ultra.passed is True
    assert ultra.critical is False

def test_preflight_reports_unreadable_video():
    checks = preflight(video_path="/no/such/clip.mp4", provider="mock", detector="claude_vision")
    video = _check(checks, "input_video_readable")
    assert video.passed is False
    assert video.critical is True


# ---------------------------------------------------------------------------
# --strict-real (Part A3)
# ---------------------------------------------------------------------------

def test_strict_real_exits_nonzero_when_key_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    rc = main(["--video", str(_fake_video(tmp_path)), "--provider", "anthropic", "--strict-real"])
    assert rc == 3

def test_strict_real_exits_nonzero_when_ultralytics_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(demo, "_module_available", lambda name: name != "ultralytics")
    monkeypatch.setattr(demo.shutil, "which", lambda name: "/usr/bin/" + name)
    rc = main(["--video", str(_fake_video(tmp_path)), "--provider", "anthropic",
               "--detector", "hybrid", "--strict-real"])
    assert rc == 3

def test_strict_real_does_not_run_pipeline_when_blocked(monkeypatch, tmp_path):
    # If it bailed correctly, analyze_clip must never have been invoked.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    called = {"ran": False}
    monkeypatch.setattr(ai, "analyze_clip", lambda **k: called.__setitem__("ran", True))
    rc = main(["--video", str(_fake_video(tmp_path)), "--provider", "anthropic", "--strict-real"])
    assert rc == 3
    assert called["ran"] is False

def test_preflight_only_returns_nonzero_when_blocked(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    rc = main(["--video", str(_fake_video(tmp_path)), "--provider", "anthropic", "--preflight-only"])
    assert rc == 1

def test_preflight_only_returns_zero_when_ok(monkeypatch, tmp_path):
    monkeypatch.setattr(demo.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    rc = main(["--video", str(_fake_video(tmp_path)), "--provider", "anthropic",
               "--detector", "claude_vision", "--preflight-only"])
    assert rc == 0


# ---------------------------------------------------------------------------
# Non-strict mock run stays transparent (Part A4 / B2)
# ---------------------------------------------------------------------------

def test_mock_run_prints_fallback_and_real_no(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    rc = main(["--video", str(_fake_video(tmp_path)), "--provider", "mock"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "=== PREFLIGHT ===" in out
    assert "REAL PIPELINE RAN: NO" in out
    assert "AI_PROVIDER is set to mock." in out


# ---------------------------------------------------------------------------
# Metadata hints threaded through the demo path (Part C)
# ---------------------------------------------------------------------------

def test_metadata_hints_threaded_into_request(monkeypatch, tmp_path):
    captured = {}

    def _fake_resolve(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    monkeypatch.setattr(
        "services.metadata.resolve_clip_game_context", _fake_resolve, raising=False
    )
    run_demo(
        str(_fake_video(tmp_path)),
        provider="mock",
        metadata_hints={"clip_date_hint": "2024-12-25", "home_team_hint": "LAL", "away_team_hint": "BOS"},
    )
    vm = captured["video_metadata"]
    assert vm["clip_date_hint"] == "2024-12-25"
    assert vm["home_team_hint"] == "LAL"
    assert vm["away_team_hint"] == "BOS"

def test_metadata_hints_reach_resolver_request():
    # End-to-end through the real registry: hints on video_metadata land on the request.
    from services.metadata import registry
    seen = {}

    class _Provider:
        def resolve_game_context(self, request):
            seen["request"] = request
            from services.metadata.models import ResolvedGameContext
            return ResolvedGameContext(resolution_status="unresolved")

    import services.metadata.registry as reg
    orig = reg.get_metadata_provider
    reg.get_metadata_provider = lambda sport: _Provider()
    try:
        registry.resolve_clip_game_context(
            sport="basketball",
            video_metadata={"filename": "NBA_GAME.mp4", "clip_date_hint": "2024-12-25",
                            "home_team_hint": "LAL", "away_team_hint": "BOS"},
        )
    finally:
        reg.get_metadata_provider = orig
    req = seen["request"]
    assert req.clip_date_hint == "2024-12-25"
    assert req.home_team_hint == "LAL"
    assert req.away_team_hint == "BOS"

def test_metadata_hints_omitted_when_empty(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])

    def _fake_resolve(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(
        "services.metadata.resolve_clip_game_context", _fake_resolve, raising=False
    )
    run_demo(str(_fake_video(tmp_path)), provider="mock", metadata_hints={"clip_date_hint": None})
    vm = captured["video_metadata"]
    assert "clip_date_hint" not in vm  # empty hints never pollute the metadata dict
