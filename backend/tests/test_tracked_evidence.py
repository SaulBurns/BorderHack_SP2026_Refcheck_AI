import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.ai_analyzer as ai
from services.ai_analyzer import _adjudicator_agent, _reconcile
from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    FrameDetections,
    RawDetections,
)
from services.extractors.basketball_vision import (
    movement_direction,
    summarize_tracked_evidence,
    trajectory_movement,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obj(label, x, y, w=0.2, h=0.4, track_id=None):
    return DetectionObject(
        label=label, confidence=0.9, bbox=BoundingBox(x=x, y=y, width=w, height=h), track_id=track_id
    )

def _dets(*frame_object_lists):
    return RawDetections(
        model="t",
        detector_version="t",
        frames=[FrameDetections(frame_index=i, objects=list(objs)) for i, objs in enumerate(frame_object_lists)],
    )

def _bbox(x, y, w=0.2, h=0.4):
    return BoundingBox(x=x, y=y, width=w, height=h)


# ---------------------------------------------------------------------------
# trajectory_movement — uses all frames (temporal continuity)
# ---------------------------------------------------------------------------

def test_trajectory_movement_none_for_single_point():
    assert trajectory_movement([(0, _bbox(0.5, 0.5))]) is None

def test_trajectory_movement_two_point_matches_endpoints():
    # Two points reduce to net displacement, same as movement_direction.
    assert trajectory_movement([(0, _bbox(0.3, 0.5)), (1, _bbox(0.7, 0.5))]) == "lateral"

def test_trajectory_movement_robust_to_endpoint_jitter():
    # A sustained downward drive with a lateral jitter on the LAST frame.
    # Endpoint-only movement is fooled into "lateral"; the full-trajectory
    # half-split correctly reports the downward drive as "forward".
    traj = [
        (0, _bbox(0.50, 0.30)),
        (1, _bbox(0.50, 0.50)),
        (2, _bbox(0.50, 0.70)),
        (3, _bbox(0.95, 0.72)),  # lateral jitter on the final frame
    ]
    assert movement_direction(traj) == "lateral"      # endpoint-only is wrong
    assert trajectory_movement(traj) == "forward"      # temporal grounding is right

def test_trajectory_movement_stationary():
    assert trajectory_movement([(0, _bbox(0.5, 0.5)), (1, _bbox(0.5, 0.5)), (2, _bbox(0.5, 0.5))]) == "stationary"


# ---------------------------------------------------------------------------
# summarize_tracked_evidence — identities, timeline, confidence
# ---------------------------------------------------------------------------

def test_summary_none_when_no_objects():
    assert summarize_tracked_evidence(None) is None
    assert summarize_tracked_evidence(_dets([])) is None

def test_summary_surfaces_offensive_and_defender_identity():
    dets = _dets(
        [
            _obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1),   # ball handler
            _obj("sports ball", 0.5, 0.5, 0.05, 0.05),
            _obj("person", 0.7, 0.5, 0.2, 0.6, track_id=2),   # defender
        ],
        [
            _obj("person", 0.55, 0.5, 0.3, 0.8, track_id=1),
            _obj("sports ball", 0.55, 0.5, 0.05, 0.05),
            _obj("person", 0.75, 0.5, 0.2, 0.6, track_id=2),
        ],
    )
    ev = summarize_tracked_evidence(dets)
    assert ev["ball_handler_track_id"] == 1          # offensive identity now surfaced
    assert ev["ball_handler_control_frames"] == 2
    assert ev["defender_track_id"] == 2              # defender identity now surfaced
    assert ev["defender_present"] is True
    assert ev["players_tracked"] == 2
    assert ev["frames_with_ball"] == 2

def test_summary_possession_timeline_and_changes():
    # Ball moves from player 1 (frame 0) to player 2 (frame 1) -> one change.
    dets = _dets(
        [_obj("person", 0.3, 0.5, 0.3, 0.8, track_id=1), _obj("sports ball", 0.3, 0.5, 0.05, 0.05)],
        [_obj("person", 0.7, 0.5, 0.3, 0.8, track_id=2), _obj("sports ball", 0.7, 0.5, 0.05, 0.05)],
    )
    ev = summarize_tracked_evidence(dets)
    assert ev["possession_timeline"] == [
        {"frame_index": 0, "controller_track_id": 1},
        {"frame_index": 1, "controller_track_id": 2},
    ]
    assert ev["possession_changes"] == 1
    assert ev["possession_summary"] == "passing"

def test_summary_tracking_confidence_bounds_and_scaling():
    strong = summarize_tracked_evidence(_dets(
        [
            _obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1),
            _obj("sports ball", 0.5, 0.5, 0.05, 0.05),
            _obj("person", 0.7, 0.5, 0.2, 0.6, track_id=2),
        ],
        [
            _obj("person", 0.55, 0.5, 0.3, 0.8, track_id=1),
            _obj("sports ball", 0.55, 0.5, 0.05, 0.05),
            _obj("person", 0.75, 0.5, 0.2, 0.6, track_id=2),
        ],
    ))
    # ball every frame (0.4) + 2 players (0.3) + handler id (0.2) + defender (0.1) = 1.0
    assert strong["tracking_confidence"] == 1.0

    weak = summarize_tracked_evidence(_dets([_obj("person", 0.2, 0.5, 0.1, 0.2, track_id=9)]))
    assert 0.0 <= weak["tracking_confidence"] <= 0.2  # no ball, single player


# ---------------------------------------------------------------------------
# Adjudicator prompt now carries tracked evidence (what reaches Claude)
# ---------------------------------------------------------------------------

def _capture_prompt(monkeypatch):
    captured = {}
    valid = ('{"verdict":"fair_call","confidence":0.6,"primary_rule_id":null,'
             '"supporting_rule_ids":[],"reasoning":"r","flags":[]}')

    def fake_call(*, system_prompt, user_content, temperature, max_tokens=1200):
        captured["prompt"] = user_content
        return valid

    monkeypatch.setattr(ai, "_call_anthropic_messages", fake_call)
    return captured

def test_adjudicator_includes_tracked_evidence_when_present(monkeypatch):
    captured = _capture_prompt(monkeypatch)
    _adjudicator_agent(
        perception={"event_type": "possible_blocking_foul"},
        rules=[],
        original_call="",
        framing="POSTURE",
        temperature=0.2,
        sport="basketball",
        tracked_evidence={"ball_handler_track_id": 1, "defender_track_id": 2, "possession_summary": "dribbling"},
    )
    assert "TRACKED DETECTION EVIDENCE" in captured["prompt"]
    assert "ball_handler_track_id" in captured["prompt"]

def test_adjudicator_omits_tracked_evidence_when_none(monkeypatch):
    captured = _capture_prompt(monkeypatch)
    _adjudicator_agent(
        perception={"event_type": "x"},
        rules=[],
        original_call="",
        framing="POSTURE",
        temperature=0.2,
        sport="basketball",
        tracked_evidence=None,
    )
    assert "TRACKED DETECTION EVIDENCE" not in captured["prompt"]


# ---------------------------------------------------------------------------
# Confidence calibration in _reconcile (backward compatible when None)
# ---------------------------------------------------------------------------

def _adj(verdict, conf):
    return {"verdict": verdict, "confidence": conf}

def test_reconcile_unchanged_without_detection_confidence():
    perception = {"perception_confidence": 0.8, "visual_quality": "clear"}
    verdict, conf, _ = _reconcile(_adj("fair_call", 0.5), _adj("fair_call", 0.5), perception)
    assert verdict == "fair_call"
    assert conf == round((0.5 + 0.5 + 0.8) / 3, 2)  # 0.6, identical to legacy

def test_reconcile_strong_tracking_nudges_confidence_up():
    perception = {"perception_confidence": 0.8, "visual_quality": "clear"}
    base = round((0.5 + 0.5 + 0.8) / 3, 2)
    _, conf, _ = _reconcile(_adj("fair_call", 0.5), _adj("fair_call", 0.5), perception, detection_confidence=1.0)
    assert conf > base
    assert conf == round((0.5 + 0.5 + 0.8) / 3 + 0.1 * (1.0 - 0.5), 2)

def test_reconcile_weak_tracking_nudges_confidence_down():
    perception = {"perception_confidence": 0.8, "visual_quality": "clear"}
    base = round((0.5 + 0.5 + 0.8) / 3, 2)
    _, conf, _ = _reconcile(_adj("fair_call", 0.5), _adj("fair_call", 0.5), perception, detection_confidence=0.0)
    assert conf < base

def test_reconcile_calibration_only_applies_on_agreement():
    # Disagreement path ignores detection_confidence (stays inconclusive/min).
    perception = {"perception_confidence": 0.8, "visual_quality": "clear"}
    verdict, conf, _ = _reconcile(_adj("fair_call", 0.5), _adj("bad_call", 0.5), perception, detection_confidence=1.0)
    assert verdict == "inconclusive"
    assert conf == round(min(0.5, 0.5, 0.8), 2)

def test_reconcile_confidence_never_exceeds_one():
    perception = {"perception_confidence": 1.0, "visual_quality": "clear"}
    _, conf, _ = _reconcile(_adj("fair_call", 1.0), _adj("fair_call", 1.0), perception, detection_confidence=1.0)
    assert conf <= 1.0


# ---------------------------------------------------------------------------
# Pipeline threads tracked evidence to adjudication and into the result
# ---------------------------------------------------------------------------

def test_pipeline_threads_tracked_evidence(monkeypatch):
    from pathlib import Path
    from unittest.mock import MagicMock

    from services.ai_analyzer import _run_four_agent_pipeline
    from services.detectors.detection_models import DetectorResult

    dets = _dets([
        _obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1),
        _obj("sports ball", 0.5, 0.5, 0.05, 0.05),
        _obj("person", 0.7, 0.5, 0.2, 0.6, track_id=2),
    ])
    captured = {}

    class _FakeDetector:
        name = "fake"
        def detect(self, frames, sport, original_call):
            return DetectorResult(perception={"sport": sport, "event_type": "unclear"}, detections=dets)

    def fake_adjudicator(**kwargs):
        captured["tracked_evidence"] = kwargs.get("tracked_evidence")
        return {"verdict": "inconclusive", "confidence": 0.5}

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    monkeypatch.setattr(ai, "_retrieval_agent", lambda perception, sport: "q")
    monkeypatch.setattr(ai, "_retrieve_rules", lambda *a, **k: [])
    monkeypatch.setattr(ai, "_adjudicator_agent", fake_adjudicator)

    result = _run_four_agent_pipeline(
        frame_paths=[Path("f.jpg")],
        file=MagicMock(),
        sport="basketball",
        level_of_play="",
        league="",
        original_call="",
        referee_name="",
        video_metadata=None,
    )
    # Adjudicator received tracking-grounded evidence...
    assert captured["tracked_evidence"] is not None
    assert captured["tracked_evidence"]["ball_handler_track_id"] == 1
    assert captured["tracked_evidence"]["defender_track_id"] == 2
    # ...and the result carries it for confidence calibration downstream.
    assert result["tracked_evidence"]["defender_present"] is True

def test_pipeline_no_tracked_evidence_for_non_basketball(monkeypatch):
    from pathlib import Path
    from unittest.mock import MagicMock

    from services.ai_analyzer import _run_four_agent_pipeline
    from services.detectors.detection_models import DetectorResult

    dets = _dets([_obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1)])
    captured = {}

    class _FakeDetector:
        name = "fake"
        def detect(self, frames, sport, original_call):
            return DetectorResult(perception={"sport": sport}, detections=dets)

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    monkeypatch.setattr(ai, "_retrieval_agent", lambda perception, sport: "q")
    monkeypatch.setattr(ai, "_retrieve_rules", lambda *a, **k: [])
    monkeypatch.setattr(ai, "_adjudicator_agent",
                        lambda **k: captured.setdefault("te", k.get("tracked_evidence")) or {"verdict": "inconclusive", "confidence": 0.5})

    result = _run_four_agent_pipeline(
        frame_paths=[Path("f.jpg")], file=MagicMock(), sport="hockey",
        level_of_play="", league="", original_call="", referee_name="", video_metadata=None,
    )
    assert captured["te"] is None
    assert result["tracked_evidence"] is None
