import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import services.ai_analyzer as ai
from services.ai_analyzer import _build_response
from scripts.demo_analyze import format_report, main, run_demo


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
    assert "REAL pipeline ran (not mock/fallback): False" in report
    assert "fallback_reason" in report

def test_format_report_flags_real_as_true():
    resp = {
        "verdict": {"verdict": "fair_call", "confidence": 0.7, "cited_rule": {"rule_id": "BLOCK_CHARGE", "section_title": "x"}, "reasoning": "r"},
        "diagnostics": {"provider_used": "anthropic_four_agent", "detector": "claude_vision", "fallback_reason": None},
    }
    assert "REAL pipeline ran (not mock/fallback): True" in format_report(resp)

def test_main_smoke(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    rc = main(["--video", str(_fake_video(tmp_path)), "--provider", "mock"])
    assert rc == 0
    assert "WHAT ACTUALLY RAN" in capsys.readouterr().out

def test_main_missing_file_returns_2(tmp_path):
    assert main(["--video", str(tmp_path / "nope.mp4"), "--provider", "mock"]) == 2
