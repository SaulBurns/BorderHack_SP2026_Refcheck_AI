import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from unittest.mock import MagicMock

import services.ai_analyzer as ai
from services.ai_analyzer import _build_response, _frontend_perception, _run_four_agent_pipeline, analyze_clip
from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    DetectorResult,
    FrameDetections,
    RawDetections,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obj(label, x, y, w, h):
    return DetectionObject(label=label, confidence=0.9, bbox=BoundingBox(x=x, y=y, width=w, height=h))

def _controlled_detections():
    # ball center inside the player's box -> "gathered"
    return RawDetections(
        model="yolov8n.pt",
        detector_version="0.1.0",
        frames=[FrameDetections(frame_index=0, objects=[
            _obj("person", 0.5, 0.5, 0.4, 0.8),
            _obj("sports ball", 0.5, 0.5, 0.05, 0.05),
        ])],
    )

def _loose_detections():
    return RawDetections(
        model="yolov8n.pt",
        detector_version="0.1.0",
        frames=[FrameDetections(frame_index=0, objects=[
            _obj("person", 0.2, 0.5, 0.1, 0.2),
            _obj("sports ball", 0.9, 0.9, 0.05, 0.05),
        ])],
    )

_NEUTRAL_PERCEPTION = {  # what a pure YOLO baseline perception looks like
    "sport": "basketball",
    "event_type": "unclear",
    "summary": "yolo baseline",
    "perception_confidence": 0.0,
}

_CLAUDE_PERCEPTION = {  # full Claude perception
    "sport": "basketball",
    "event_type": "possible_blocking_foul",
    "summary": "claude",
    "offensive_control_status": "airborne_shooter",
    "defender_status": {
        "primary_or_secondary": "secondary",
        "legal_guarding_position": "not_established",
        "feet_set_before_contact": False,
        "moving_direction": "lateral",
        "inside_restricted_area": True,
    },
    "court_geometry": {
        "key_zone": "restricted_area",
        "restricted_area_arc_visible": True,
        "defender_feet_visible": True,
        "basket_visible": True,
    },
    "perception_confidence": 0.8,
}


# ---------------------------------------------------------------------------
# _frontend_perception — claude_vision / yolov8 / hybrid behaviors
# ---------------------------------------------------------------------------

def test_claude_vision_path_no_detections_preserves_behavior():
    out = _frontend_perception(_CLAUDE_PERCEPTION, "anthropic_four_agent", "basketball")  # detections=None
    sd = out["sport_details"]["basketball"]
    # sport_details mirrors perception (no detection override).
    assert sd["offensive_control_status"] == "airborne_shooter"
    assert sd["defender_status"]["legal_guarding_position"] == "not_established"
    # legacy top-level fields still present and equal.
    assert out["offensive_control_status"] == "airborne_shooter"
    assert out["defender_status"]["legal_guarding_position"] == "not_established"

def test_yolov8_path_derives_offensive_control_from_detections():
    out = _frontend_perception(_NEUTRAL_PERCEPTION, "anthropic_four_agent", "basketball", _controlled_detections())
    sd = out["sport_details"]["basketball"]
    assert sd["offensive_control_status"] == "gathered"  # derived from detections
    # legacy top-level offensive_control_status reflects the (neutral) perception, unchanged.
    assert out["offensive_control_status"] == "unclear"

def test_yolov8_path_loose_ball():
    out = _frontend_perception(_NEUTRAL_PERCEPTION, "x", "basketball", _loose_detections())
    assert out["sport_details"]["basketball"]["offensive_control_status"] == "loose_ball"

def test_hybrid_path_enriches_offensive_keeps_claude_geometry():
    out = _frontend_perception(_CLAUDE_PERCEPTION, "x", "basketball", _controlled_detections())
    sd = out["sport_details"]["basketball"]
    assert sd["offensive_control_status"] == "gathered"  # derived (overrides claude's value)
    assert sd["defender_status"]["legal_guarding_position"] == "not_established"  # from claude
    assert sd["court_geometry"]["key_zone"] == "restricted_area"  # from claude
    # legacy top-level remains the claude value.
    assert out["offensive_control_status"] == "airborne_shooter"


# ---------------------------------------------------------------------------
# Detection-present vs detection-absent
# ---------------------------------------------------------------------------

def test_detection_present_vs_absent_legacy_identical():
    absent = _frontend_perception(_CLAUDE_PERCEPTION, "x", "basketball")
    present = _frontend_perception(_CLAUDE_PERCEPTION, "x", "basketball", _controlled_detections())

    # sport_details diverges (detections enrich it)...
    assert absent["sport_details"]["basketball"]["offensive_control_status"] == "airborne_shooter"
    assert present["sport_details"]["basketball"]["offensive_control_status"] == "gathered"

    # ...but every legacy top-level field is identical (backward compatible).
    for key in ("offensive_control_status", "defender_status", "court_geometry",
                "ball_state", "contact_detected", "visual_quality"):
        assert absent[key] == present[key]


def test_non_basketball_sport_details_unaffected_by_detections():
    # Hockey extractor ignores detections; sport_details stays the placeholder.
    absent = _frontend_perception({"sport": "hockey"}, "x", "hockey")
    present = _frontend_perception({"sport": "hockey"}, "x", "hockey", _controlled_detections())
    assert absent["sport_details"] == present["sport_details"]
    assert "hockey" in present["sport_details"]


# ---------------------------------------------------------------------------
# _build_response threads detections from agent_result
# ---------------------------------------------------------------------------

def _agent_result(perception, detections=None):
    result = {
        "provider_used": "anthropic_four_agent",
        "rules": [],
        "perception": perception,
        "adjudicator_a": {"verdict": "inconclusive", "confidence": 0.5, "primary_rule_id": None, "reasoning": "r", "flags": []},
        "adjudicator_b": {"verdict": "inconclusive", "confidence": 0.5, "primary_rule_id": None, "reasoning": "r", "flags": []},
    }
    if detections is not None:
        result["detections"] = detections
    return result

def test_build_response_uses_detections_when_present():
    resp = _build_response(
        agent_result=_agent_result(_NEUTRAL_PERCEPTION, _controlled_detections()),
        clip_id="abc123",
        frame_paths=[],
        video_metadata=None,
        processing_time_seconds=1.0,
        sport="basketball",
    )
    sd = resp["verdict"]["perception"]["sport_details"]["basketball"]
    assert sd["offensive_control_status"] == "gathered"

def test_build_response_without_detections_preserves_behavior():
    resp = _build_response(
        agent_result=_agent_result(_CLAUDE_PERCEPTION),  # no "detections" key
        clip_id="abc123",
        frame_paths=[],
        video_metadata=None,
        processing_time_seconds=1.0,
        sport="basketball",
    )
    sd = resp["verdict"]["perception"]["sport_details"]["basketball"]
    assert sd["offensive_control_status"] == "airborne_shooter"


# ---------------------------------------------------------------------------
# _run_four_agent_pipeline threads detections from the detector
# ---------------------------------------------------------------------------

def test_pipeline_threads_detections_into_agent_result(monkeypatch):
    detections = _controlled_detections()

    class _FakeDetector:
        name = "fake"
        def detect(self, frames, sport, original_call):
            return DetectorResult(perception={"sport": sport, "event_type": "unclear"}, detections=detections)

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    monkeypatch.setattr(ai, "_adjudicator_agent", lambda **k: {"verdict": "inconclusive", "confidence": 0.5})

    result = _run_four_agent_pipeline(
        frame_paths=[Path("frame.jpg")],
        file=MagicMock(),
        sport="basketball",
        level_of_play="",
        league="",
        original_call="",
        referee_name="",
        video_metadata=None,
    )
    assert result["detections"] is detections


def test_mock_path_has_no_detections(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    result = _run_four_agent_pipeline(
        frame_paths=[Path("frame.jpg")],
        file=MagicMock(),
        sport="basketball",
        level_of_play="",
        league="",
        original_call="",
        referee_name="",
        video_metadata=None,
    )
    assert result.get("detections") is None  # mock path -> no detections


# ---------------------------------------------------------------------------
# analyze_clip end-to-end wiring
# ---------------------------------------------------------------------------

def test_analyze_clip_end_to_end_applies_detections(monkeypatch):
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    monkeypatch.setattr(
        ai,
        "_run_four_agent_pipeline",
        lambda **kwargs: _agent_result(_NEUTRAL_PERCEPTION, _controlled_detections()),
    )
    response = analyze_clip(file=MagicMock(), sport="basketball", video_metadata=None)
    sd = response["verdict"]["perception"]["sport_details"]["basketball"]
    assert sd["offensive_control_status"] == "gathered"
