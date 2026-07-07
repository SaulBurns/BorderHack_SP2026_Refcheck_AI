import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

import services.ai_analyzer as ai
import services.metadata as metadata
from services.ai_analyzer import analyze_clip


def _file():
    return SimpleNamespace(filename="random_clip.mp4", content_type="video/mp4")


def _basketball_metadata(filename="random_clip.mp4"):
    return {"filename": filename, "stored_path": "", "size_bytes": 0}


def test_basketball_response_includes_game_context(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    response = analyze_clip(file=_file(), sport="basketball", video_metadata=_basketball_metadata())
    assert "game_context" in response
    # No date/team hints in the filename -> skipped, no nba_api call.
    assert response["game_context"]["resolution_status"] == "skipped"
    assert response["game_context"]["provider"] == "nba"
    # Verdict is untouched.
    assert "verdict" in response and "perception" in response["verdict"]


def test_non_basketball_response_has_no_game_context(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    response = analyze_clip(file=_file(), sport="hockey", video_metadata=_basketball_metadata())
    assert "game_context" not in response
    assert "verdict" in response


def test_metadata_failure_does_not_break_verdict(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])

    def _boom(**kwargs):
        raise RuntimeError("metadata subsystem exploded")

    monkeypatch.setattr(metadata, "resolve_clip_game_context", _boom)
    response = analyze_clip(file=_file(), sport="basketball", video_metadata=_basketball_metadata())
    # Enrichment failure is swallowed; verdict still returned.
    assert "verdict" in response
    assert "game_context" not in response
