"""Sprint 6 performance-optimization tests.

Lock in the caching / dedup / parallelization behaviors without changing the
observable API contract:

  * frame-extraction cache (reuse frames on disk, skip ffprobe+ffmpeg)
  * provider-instance cache (reuse across calls, re-resolve on AI_PROVIDER change)
  * rule-records + ranking memoization
  * concurrent adjudicators (real overlap; identical outputs; error propagation)
  * opt-in analysis result cache (default OFF => unchanged behavior)
"""

import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import services.ai_analyzer as ai
from services.analysis import frames as frames_mod


# ---------------------------------------------------------------------------
# Frame-extraction cache
# ---------------------------------------------------------------------------

def test_extract_frames_reuses_cached_frames(monkeypatch, tmp_path):
    clip_id = "cachedclip"
    frame_dir = tmp_path / clip_id
    frame_dir.mkdir(parents=True)
    for i in range(1, 4):
        (frame_dir / f"frame_{i:03d}.jpg").write_bytes(b"x")
    monkeypatch.setattr(frames_mod, "FRAME_DIR", tmp_path)

    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fakevideo")

    def _boom(*a, **k):
        raise AssertionError("ffprobe/ffmpeg must not run when frames are cached")

    monkeypatch.setattr(frames_mod.subprocess, "run", _boom)

    frames = ai._extract_frames(str(video), clip_id)
    assert len(frames) == 3
    assert all(f.name.startswith("frame_") for f in frames)


def test_extract_frames_extracts_when_no_cache(monkeypatch, tmp_path):
    clip_id = "freshclip"
    monkeypatch.setattr(frames_mod, "FRAME_DIR", tmp_path)
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fakevideo")

    calls = {"run": 0}

    def _fake_run(cmd, *a, **k):
        calls["run"] += 1
        # Simulate ffmpeg writing frames on the extraction call (has -frames:v).
        if "-frames:v" in cmd:
            out = tmp_path / clip_id
            out.mkdir(parents=True, exist_ok=True)
            (out / "frame_001.jpg").write_bytes(b"x")
        return MagicMock(stdout="2.0")

    monkeypatch.setattr(frames_mod.subprocess, "run", _fake_run)
    frames = ai._extract_frames(str(video), clip_id)
    assert len(frames) == 1
    assert calls["run"] >= 1  # ffmpeg ran on the cold path


# ---------------------------------------------------------------------------
# Provider-instance cache
# ---------------------------------------------------------------------------

def test_active_provider_caches_instance(monkeypatch):
    ai._reset_provider_cache()
    monkeypatch.setenv("AI_PROVIDER", "mock")
    first = ai._active_provider()
    second = ai._active_provider()
    assert first is second  # reused within a process


def test_active_provider_reresolves_on_env_change(monkeypatch):
    ai._reset_provider_cache()
    monkeypatch.setenv("AI_PROVIDER", "mock")
    mock_provider = ai._active_provider()
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    anthropic_provider = ai._active_provider()
    assert mock_provider is not anthropic_provider
    assert anthropic_provider.provider_name() == "anthropic"


def test_reset_provider_cache_forces_new_instance(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    ai._reset_provider_cache()
    first = ai._active_provider()
    ai._reset_provider_cache()
    second = ai._active_provider()
    assert first is not second


# ---------------------------------------------------------------------------
# Rule-records + ranking memoization
# ---------------------------------------------------------------------------

def test_rule_records_cached_identity():
    a = ai._rule_records("basketball")
    b = ai._rule_records("basketball")
    assert a is b  # lru_cache returns the same object
    assert isinstance(a, tuple)


def test_retrieve_rules_returns_list_and_is_memoized():
    perception = {"event_type": "possible_blocking_foul", "summary": "drive to the rim"}
    first = ai._retrieve_rules("restricted area secondary defender", perception, "basketball")
    second = ai._retrieve_rules("restricted area secondary defender", perception, "basketball")
    assert isinstance(first, list)
    assert [r["rule_id"] for r in first] == [r["rule_id"] for r in second]


# ---------------------------------------------------------------------------
# Concurrent adjudicators — real overlap, identical output, error propagation
# ---------------------------------------------------------------------------

def _pipeline_kwargs(sport="basketball"):
    return dict(
        frame_paths=[Path("f.jpg")],
        file=MagicMock(),
        sport=sport,
        level_of_play="",
        league="",
        original_call="",
        referee_name="",
        video_metadata=None,
    )


def test_adjudicators_run_concurrently(monkeypatch):
    from services.detectors.detection_models import DetectorResult

    barrier = threading.Barrier(2, timeout=5)
    overlapped = {"ok": False}

    class _FakeDetector:
        name = "fake"
        def detect(self, frames, sport, original_call):
            return DetectorResult(perception={"sport": sport, "event_type": "x"}, detections=None)

    def send(*, system_prompt, user_content, temperature, max_tokens=1200):
        if "POSTURE" in system_prompt or "REASONING POSTURE" in system_prompt:
            # Only the two adjudicator calls carry a framing posture; block until
            # both are in-flight to prove they overlap.
            try:
                barrier.wait()
                overlapped["ok"] = True
            except threading.BrokenBarrierError:
                pass
        return '{"verdict":"fair_call","confidence":0.6}'

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    monkeypatch.setattr(ai, "_retrieval_agent", lambda perception, sport: "q")
    monkeypatch.setattr(ai, "_retrieve_rules", lambda *a, **k: [])
    monkeypatch.setattr(ai, "_send_messages", send)

    result = ai._run_four_agent_pipeline(**_pipeline_kwargs())
    assert overlapped["ok"] is True  # both adjudicators were in-flight simultaneously
    assert result["adjudicator_a"]["verdict"] == "fair_call"
    assert result["adjudicator_b"]["verdict"] == "fair_call"


def test_adjudicator_failure_falls_back_to_mock(monkeypatch):
    from services.detectors.detection_models import DetectorResult

    class _FakeDetector:
        name = "fake"
        def detect(self, frames, sport, original_call):
            return DetectorResult(perception={"sport": sport, "event_type": "x"}, detections=None)

    def send(*, system_prompt, user_content, temperature, max_tokens=1200):
        if "REASONING POSTURE" in system_prompt:
            raise RuntimeError("adjudicator boom")
        return '{"verdict":"fair_call","confidence":0.6}'

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    monkeypatch.setattr(ai, "_retrieval_agent", lambda perception, sport: "q")
    monkeypatch.setattr(ai, "_retrieve_rules", lambda *a, **k: [])
    monkeypatch.setattr(ai, "_send_messages", send)

    result = ai._run_four_agent_pipeline(**_pipeline_kwargs())
    # A thread failure re-raises through .result() and hits the mock fallback.
    assert result["provider_used"] == "mock"
    assert "adjudicator boom" in result["fallback_reason"]


# ---------------------------------------------------------------------------
# Opt-in analysis result cache
# ---------------------------------------------------------------------------

def _count_pipeline_calls(monkeypatch):
    calls = {"n": 0}
    agent_result = {
        "provider_used": "anthropic_four_agent",
        "retrieval_query": "q",
        "retrieved_rules": [],
        "perception": {"sport": "basketball", "event_type": "unclear", "perception_confidence": 0.8, "visual_quality": "clear"},
        "adjudicator_a": {"verdict": "fair_call", "confidence": 0.6, "primary_rule_id": None, "reasoning": "r", "flags": []},
        "adjudicator_b": {"verdict": "fair_call", "confidence": 0.6, "primary_rule_id": None, "reasoning": "r", "flags": []},
    }

    def fake_pipeline(**kwargs):
        calls["n"] += 1
        return dict(agent_result)

    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    monkeypatch.setattr(ai, "_run_four_agent_pipeline", fake_pipeline)
    return calls


def test_result_cache_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ANALYSIS_CACHE", raising=False)
    ai._reset_result_cache()
    calls = _count_pipeline_calls(monkeypatch)
    meta = {"stored_path": "/tmp/x.mp4", "size_bytes": 10}
    ai.analyze_clip(file=MagicMock(), sport="basketball", video_metadata=meta)
    ai.analyze_clip(file=MagicMock(), sport="basketball", video_metadata=meta)
    assert calls["n"] == 2  # no caching: pipeline runs every time (unchanged behavior)


def test_result_cache_hits_when_enabled(monkeypatch):
    monkeypatch.setenv("ANALYSIS_CACHE", "1")
    ai._reset_result_cache()
    calls = _count_pipeline_calls(monkeypatch)
    meta = {"stored_path": "/tmp/x.mp4", "size_bytes": 10}
    first = ai.analyze_clip(file=MagicMock(), sport="basketball", video_metadata=meta)
    second = ai.analyze_clip(file=MagicMock(), sport="basketball", video_metadata=meta)
    assert calls["n"] == 1  # second analysis served from cache, zero model calls
    assert first["clip_id"] == second["clip_id"]
    assert first["verdict"]["verdict"] == second["verdict"]["verdict"]


def test_result_cache_returns_independent_copy(monkeypatch):
    monkeypatch.setenv("ANALYSIS_CACHE", "1")
    ai._reset_result_cache()
    _count_pipeline_calls(monkeypatch)
    meta = {"stored_path": "/tmp/y.mp4", "size_bytes": 20}
    first = ai.analyze_clip(file=MagicMock(), sport="basketball", video_metadata=meta)
    first["verdict"]["verdict"] = "MUTATED"
    second = ai.analyze_clip(file=MagicMock(), sport="basketball", video_metadata=meta)
    assert second["verdict"]["verdict"] != "MUTATED"  # cache not corrupted by caller mutation


def test_result_cache_key_varies_by_inputs(monkeypatch):
    monkeypatch.setenv("ANALYSIS_CACHE", "1")
    ai._reset_result_cache()
    calls = _count_pipeline_calls(monkeypatch)
    meta = {"stored_path": "/tmp/z.mp4", "size_bytes": 30}
    ai.analyze_clip(file=MagicMock(), sport="basketball", original_call="charge", video_metadata=meta)
    ai.analyze_clip(file=MagicMock(), sport="basketball", original_call="block", video_metadata=meta)
    assert calls["n"] == 2  # different original_call => distinct cache entries
