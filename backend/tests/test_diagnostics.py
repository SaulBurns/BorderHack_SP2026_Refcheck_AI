import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from types import SimpleNamespace

import services.ai_analyzer as ai
import services.metadata as metadata
from services.ai_analyzer import _build_response, analyze_clip
from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    FrameDetections,
    RawDetections,
)


def _dets(frames):
    """frames: list of list of (label, track_id)."""
    out = []
    for i, objs in enumerate(frames):
        objects = [
            DetectionObject(
                label=label,
                confidence=0.9,
                bbox=BoundingBox(x=0.5, y=0.5, width=0.1, height=0.2),
                track_id=tid,
            )
            for (label, tid) in objs
        ]
        out.append(FrameDetections(frame_index=i, objects=objects))
    return RawDetections(model="yolov8n.pt", detector_version="0.2.0", frames=out)


def _agent_result(perception=None, detector=None, detections=None, provider_used="anthropic_four_agent"):
    result = {
        "provider_used": provider_used,
        "retrieval_query": "q",
        "retrieved_rules": [],
        "perception": perception or {"sport": "basketball", "event_type": "unclear"},
        "adjudicator_a": {"verdict": "inconclusive", "confidence": 0.5, "primary_rule_id": None, "reasoning": "r", "flags": []},
        "adjudicator_b": {"verdict": "inconclusive", "confidence": 0.5, "primary_rule_id": None, "reasoning": "r", "flags": []},
    }
    if detector is not None:
        result["detector"] = detector
    if detections is not None:
        result["detections"] = detections
    return result


def _diag(agent_result, frame_paths=("f0.jpg", "f1.jpg")):
    resp = _build_response(
        agent_result=agent_result,
        clip_id="abc",
        frame_paths=[Path(p) for p in frame_paths],
        video_metadata=None,
        processing_time_seconds=1.0,
        sport="basketball",
    )
    return resp["diagnostics"]


# ---------------------------------------------------------------------------
# Detector path reflected
# ---------------------------------------------------------------------------

def test_diagnostics_claude_vision_no_detections():
    d = _diag(_agent_result(detector="claude_vision", detections=None))
    assert d["detector"] == "claude_vision"
    assert d["detections_present"] is False
    assert d["tracking_present"] is False
    assert d["sport_details_source"] == "perception"
    assert d["frames_analyzed"] == 2

def test_diagnostics_mock_detector():
    d = _diag(_agent_result(provider_used="mock"))  # no detector key
    assert d["detector"] == "mock"

def test_diagnostics_hybrid_with_tracked_detections():
    dets = _dets([[("person", 1), ("sports ball", 2)], [("person", 1)]])
    d = _diag(_agent_result(detector="hybrid", detections=dets))
    assert d["detector"] == "hybrid"
    assert d["detections_present"] is True
    assert d["tracking_present"] is True
    assert d["tracked_object_count"] == 3
    assert d["player_count"] == 1  # same track_id across frames -> one player
    assert d["ball_present"] is True
    assert d["sport_details_source"] == "detections"

def test_diagnostics_detections_without_tracking():
    dets = _dets([[("person", None), ("sports ball", None)]])
    d = _diag(_agent_result(detector="yolov8", detections=dets))
    assert d["detections_present"] is True
    assert d["tracking_present"] is False
    assert d["tracked_object_count"] == 0
    assert d["player_count"] == 1


# ---------------------------------------------------------------------------
# Metadata status reflected (via analyze_clip)
# ---------------------------------------------------------------------------

def _run_analyze(monkeypatch, sport, filename="random_clip.mp4"):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    file = SimpleNamespace(filename=filename, content_type="video/mp4")
    vm = {"filename": filename, "stored_path": "", "size_bytes": 0}
    return analyze_clip(file=file, sport=sport, video_metadata=vm)

def test_metadata_status_basketball_skipped(monkeypatch):
    resp = _run_analyze(monkeypatch, "basketball")
    diag = resp["diagnostics"]
    assert diag["metadata_attempted"] is True
    assert diag["metadata_status"] == "skipped"  # no date/team hints in filename
    assert resp["game_context"]["resolution_status"] == "skipped"

def test_metadata_not_applicable_for_non_basketball(monkeypatch):
    resp = _run_analyze(monkeypatch, "hockey")
    diag = resp["diagnostics"]
    assert diag["metadata_attempted"] is False
    assert diag["metadata_status"] == "not_applicable"
    assert "game_context" not in resp

def test_metadata_unavailable_on_failure(monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(metadata, "resolve_clip_game_context", _boom)
    resp = _run_analyze(monkeypatch, "basketball")
    diag = resp["diagnostics"]
    assert diag["metadata_status"] == "unavailable"
    # verdict still intact
    assert "verdict" in resp and "perception" in resp["verdict"]
