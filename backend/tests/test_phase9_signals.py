import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from unittest.mock import MagicMock

import services.ai_analyzer as ai
from services.ai_analyzer import _adjudicator_agent, _build_response, _run_four_agent_pipeline, analyze_clip
from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    DetectorResult,
    FrameDetections,
    RawDetections,
)

_VALID_VERDICT_JSON = (
    '{"verdict":"fair_call","confidence":0.6,"primary_rule_id":null,'
    '"supporting_rule_ids":[],"reasoning":"r","flags":[]}'
)


def _obj(label, x, y, w, h):
    return DetectionObject(label=label, confidence=0.9, bbox=BoundingBox(x=x, y=y, width=w, height=h))

def _controlled_detections():
    return RawDetections(
        model="yolov8n.pt",
        detector_version="0.1.0",
        frames=[FrameDetections(frame_index=0, objects=[
            _obj("person", 0.5, 0.5, 0.4, 0.8),
            _obj("sports ball", 0.5, 0.5, 0.05, 0.05),
        ])],
    )

def _agent_result(detections=None):
    result = {
        "provider_used": "anthropic_four_agent",
        "retrieval_query": "blocking foul",
        "retrieved_rules": [],
        "perception": {"sport": "basketball", "event_type": "unclear"},
        "adjudicator_a": {"verdict": "inconclusive", "confidence": 0.5, "primary_rule_id": None, "reasoning": "r", "flags": []},
        "adjudicator_b": {"verdict": "inconclusive", "confidence": 0.5, "primary_rule_id": None, "reasoning": "r", "flags": []},
    }
    if detections is not None:
        result["detections"] = detections
    return result


# ---------------------------------------------------------------------------
# Adjudicator prompt includes sport_details only when provided
# ---------------------------------------------------------------------------

def test_adjudicator_includes_sport_details_when_present(monkeypatch):
    captured = {}

    def fake_call(*, system_prompt, user_content, temperature, max_tokens=1200):
        captured["prompt"] = user_content
        return _VALID_VERDICT_JSON

    monkeypatch.setattr(ai, "_call_anthropic_messages", fake_call)
    _adjudicator_agent(
        perception={"event_type": "possible_blocking_foul"},
        rules=[],
        original_call="",
        framing="POSTURE",
        temperature=0.2,
        sport="basketball",
        sport_details={"basketball": {"offensive_control_status": "dribbling"}},
    )
    assert "SPORT-SPECIFIC SIGNALS" in captured["prompt"]
    assert "dribbling" in captured["prompt"]

def test_adjudicator_omits_sport_details_when_none(monkeypatch):
    captured = {}

    def fake_call(*, system_prompt, user_content, temperature, max_tokens=1200):
        captured["prompt"] = user_content
        return _VALID_VERDICT_JSON

    monkeypatch.setattr(ai, "_call_anthropic_messages", fake_call)
    _adjudicator_agent(
        perception={"event_type": "possible_blocking_foul"},
        rules=[],
        original_call="",
        framing="POSTURE",
        temperature=0.2,
        sport="basketball",
        sport_details=None,
    )
    assert "SPORT-SPECIFIC SIGNALS" not in captured["prompt"]


# ---------------------------------------------------------------------------
# Pipeline feeds sport_details to adjudication only when detections present
# ---------------------------------------------------------------------------

def _run_pipeline_capturing(monkeypatch, detections):
    captured = {}

    class _FakeDetector:
        name = "fake"
        def detect(self, frames, sport, original_call):
            return DetectorResult(perception={"sport": sport, "event_type": "unclear"}, detections=detections)

    def fake_adjudicator(**kwargs):
        captured["sport_details"] = kwargs.get("sport_details")
        return {"verdict": "inconclusive", "confidence": 0.5}

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    monkeypatch.setattr(ai, "_retrieval_agent", lambda perception, sport: "q")
    monkeypatch.setattr(ai, "_retrieve_rules", lambda *a, **k: [])
    monkeypatch.setattr(ai, "_adjudicator_agent", fake_adjudicator)

    _run_four_agent_pipeline(
        frame_paths=[Path("f.jpg")],
        file=MagicMock(),
        sport="basketball",
        level_of_play="",
        league="",
        original_call="",
        referee_name="",
        video_metadata=None,
    )
    return captured["sport_details"]

def test_pipeline_feeds_sport_details_when_detections_present(monkeypatch):
    sport_details = _run_pipeline_capturing(monkeypatch, _controlled_detections())
    assert sport_details is not None
    # The adjudicator receives the (unkeyed) BasketballDetails payload.
    assert sport_details["offensive_control_status"] == "gathered"

def test_pipeline_no_sport_details_when_detections_absent(monkeypatch):
    assert _run_pipeline_capturing(monkeypatch, None) is None


# ---------------------------------------------------------------------------
# Diagnostics block in the response
# ---------------------------------------------------------------------------

def test_diagnostics_present_with_detections():
    resp = _build_response(
        agent_result=_agent_result(_controlled_detections()),
        clip_id="abc",
        frame_paths=[],
        video_metadata=None,
        processing_time_seconds=1.0,
        sport="basketball",
    )
    diag = resp["diagnostics"]
    assert diag["detections_present"] is True
    assert diag["detection_frame_count"] == 1
    assert diag["detection_object_count"] == 2
    assert diag["sport_details_source"] == "detections"
    assert diag["provider_used"] == "anthropic_four_agent"

def test_diagnostics_without_detections_preserves_response():
    resp = _build_response(
        agent_result=_agent_result(),  # no detections
        clip_id="abc",
        frame_paths=[],
        video_metadata=None,
        processing_time_seconds=1.0,
        sport="basketball",
    )
    diag = resp["diagnostics"]
    assert diag["detections_present"] is False
    assert diag["detection_object_count"] == 0
    assert diag["sport_details_source"] == "perception"
    # existing response shape intact
    assert "clip_id" in resp and "verdict" in resp
    assert "perception" in resp["verdict"]

def test_analyze_clip_includes_diagnostics(monkeypatch):
    monkeypatch.setattr(ai, "_extract_frames", lambda *a, **k: [])
    monkeypatch.setattr(ai, "_run_four_agent_pipeline", lambda **k: _agent_result(_controlled_detections()))
    resp = analyze_clip(file=MagicMock(), sport="basketball", video_metadata=None)
    assert resp["diagnostics"]["detections_present"] is True
