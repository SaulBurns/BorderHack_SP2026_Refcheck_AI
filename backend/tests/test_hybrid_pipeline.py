import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.ai_analyzer as ai
from services.ai_analyzer import _build_response, _diagnostics_payload, _run_four_agent_pipeline
from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    DetectorResult,
    FrameDetections,
    RawDetections,
)
from services.detectors.hybrid import HybridDetector
from services.extractors.basketball_vision import (
    identify_primary_defender,
    possession_status,
    summarize_tracked_evidence,
    track_ball,
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
        model="yolov8n.pt",
        detector_version="0.2.0",
        frames=[FrameDetections(frame_index=i, objects=list(objs)) for i, objs in enumerate(frame_object_lists)],
    )

def _controlled(track_id=1, x=0.5, y=0.5, ball_y=None):
    by = y if ball_y is None else ball_y
    return [_obj("person", x, y, 0.3, 0.8, track_id=track_id), _obj("sports ball", x, by, 0.05, 0.05)]


# ---------------------------------------------------------------------------
# Ball trajectory is used whenever available
# ---------------------------------------------------------------------------

def test_track_ball_returns_sorted_per_frame_positions():
    dets = _dets(
        [_obj("sports ball", 0.5, 0.3, 0.05, 0.05)],
        [_obj("sports ball", 0.5, 0.5, 0.05, 0.05)],
        [_obj("person", 0.5, 0.5, 0.3, 0.8)],  # no ball this frame
    )
    traj = track_ball(dets)
    assert [f for f, _ in traj] == [0, 1]
    assert traj[0][1].y == 0.3 and traj[1][1].y == 0.5

def test_summary_includes_ball_movement_from_ball_path():
    # Ball drives downward (y increasing) across frames -> "forward".
    dets = _dets(
        [_obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1), _obj("sports ball", 0.5, 0.30, 0.05, 0.05)],
        [_obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1), _obj("sports ball", 0.5, 0.50, 0.05, 0.05)],
        [_obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1), _obj("sports ball", 0.5, 0.70, 0.05, 0.05)],
    )
    ev = summarize_tracked_evidence(dets)
    assert ev["ball_movement"] == "forward"

def test_ball_movement_none_when_ball_in_single_frame():
    dets = _dets([_obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1), _obj("sports ball", 0.5, 0.5, 0.05, 0.05)])
    assert summarize_tracked_evidence(dets)["ball_movement"] is None


# ---------------------------------------------------------------------------
# Deduplicated computation still agrees with the public helpers
# ---------------------------------------------------------------------------

def test_summary_shares_scan_with_public_helpers():
    dets = _dets(
        [_obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1), _obj("sports ball", 0.5, 0.5, 0.05, 0.05),
         _obj("person", 0.7, 0.5, 0.2, 0.6, track_id=2)],
        [_obj("person", 0.55, 0.5, 0.3, 0.8, track_id=1), _obj("sports ball", 0.55, 0.5, 0.05, 0.05),
         _obj("person", 0.75, 0.5, 0.2, 0.6, track_id=2)],
    )
    ev = summarize_tracked_evidence(dets)
    # The single-scan evidence must match the standalone public functions exactly.
    assert ev["possession_summary"] == possession_status(dets)
    assert ev["defender_track_id"] == identify_primary_defender(dets)[0]

def test_controlling_person_evaluated_once_per_frame(monkeypatch):
    # Prove the dedup: _controlling_person runs exactly once per ball frame during
    # summarize (not 2-3x as before the single-scan refactor).
    import services.extractors.basketball_vision as bv
    calls = {"n": 0}
    real = bv._controlling_person
    def counting(frame):
        calls["n"] += 1
        return real(frame)
    monkeypatch.setattr(bv, "_controlling_person", counting)
    dets = _dets(_controlled(1), _controlled(1, x=0.55))  # 2 ball frames
    bv.summarize_tracked_evidence(dets)
    assert calls["n"] == 2  # one evaluation per ball frame


# ---------------------------------------------------------------------------
# Graceful degradation: YOLO failure keeps Claude perception
# ---------------------------------------------------------------------------

class _FakeClaude:
    def detect(self, frames, sport, original_call):
        return DetectorResult(perception={"sport": sport, "event_type": "possible_foul"}, detections=None)

class _FailingYolo:
    def infer(self, frames):
        raise RuntimeError("ultralytics is not importable")

def test_hybrid_degrades_to_claude_when_yolo_fails():
    hybrid = HybridDetector(claude_detector=_FakeClaude(), yolo_detector=_FailingYolo())
    result = hybrid.detect([Path("f.jpg")], "basketball", "")
    assert result.perception["event_type"] == "possible_foul"  # Claude preserved
    assert result.detections is None                            # tracking dropped, no raise

def test_pipeline_does_not_fall_back_to_mock_when_yolo_fails(monkeypatch):
    # End-to-end: hybrid YOLO failure must NOT collapse the real pipeline to mock.
    captured = {}
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ai, "get_detector",
                        lambda name=None: HybridDetector(claude_detector=_FakeClaude(), yolo_detector=_FailingYolo()))
    monkeypatch.setattr(ai, "_retrieval_agent", lambda perception, sport: "q")
    monkeypatch.setattr(ai, "_retrieve_rules", lambda *a, **k: [])
    monkeypatch.setattr(ai, "_adjudicator_agent",
                        lambda **k: captured.setdefault("te", k.get("tracked_evidence")) or
                        {"verdict": "inconclusive", "confidence": 0.5})
    result = _run_four_agent_pipeline(
        frame_paths=[Path("f.jpg")], file=MagicMock(), sport="basketball",
        level_of_play="", league="", original_call="", referee_name="", video_metadata=None,
    )
    assert result["provider_used"] == "anthropic_four_agent"  # real pipeline ran
    assert result["detections"] is None                        # degraded, no tracking
    assert result["tracked_evidence"] is None
    assert captured["te"] is None                              # adjudicators still ran


# ---------------------------------------------------------------------------
# Tracked evidence reaches BOTH adjudicators
# ---------------------------------------------------------------------------

def test_tracked_evidence_reaches_both_adjudicators(monkeypatch):
    dets = _dets(_controlled(1) + [_obj("person", 0.75, 0.5, 0.2, 0.6, track_id=2)],
                 _controlled(1, x=0.55) + [_obj("person", 0.8, 0.5, 0.2, 0.6, track_id=2)])
    seen = []

    class _FakeDetector:
        name = "hybrid"
        def detect(self, frames, sport, original_call):
            return DetectorResult(perception={"sport": sport, "event_type": "x"}, detections=dets)

    def fake_adjudicator(**kwargs):
        seen.append(kwargs.get("tracked_evidence"))
        return {"verdict": "inconclusive", "confidence": 0.5}

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    monkeypatch.setattr(ai, "_retrieval_agent", lambda perception, sport: "q")
    monkeypatch.setattr(ai, "_retrieve_rules", lambda *a, **k: [])
    monkeypatch.setattr(ai, "_adjudicator_agent", fake_adjudicator)
    _run_four_agent_pipeline(
        frame_paths=[Path("f.jpg")], file=MagicMock(), sport="basketball",
        level_of_play="", league="", original_call="", referee_name="", video_metadata=None,
    )
    assert len(seen) == 2                       # both adjudicators called
    assert all(te is not None for te in seen)   # both received tracked evidence
    assert seen[0] is seen[1]                    # same object (computed once, not per-adjudicator)


# ---------------------------------------------------------------------------
# Reconciliation uses tracking confidence
# ---------------------------------------------------------------------------

def _agent_result(tracked_evidence=None, detections=None):
    result = {
        "provider_used": "anthropic_four_agent",
        "detector": "hybrid",
        "retrieval_query": "q",
        "retrieved_rules": [],
        "perception": {"sport": "basketball", "event_type": "x", "perception_confidence": 0.8, "visual_quality": "clear"},
        "adjudicator_a": {"verdict": "fair_call", "confidence": 0.7, "primary_rule_id": None, "reasoning": "r", "flags": []},
        "adjudicator_b": {"verdict": "fair_call", "confidence": 0.7, "primary_rule_id": None, "reasoning": "r", "flags": []},
    }
    if tracked_evidence is not None:
        result["tracked_evidence"] = tracked_evidence
    if detections is not None:
        result["detections"] = detections
    return result

def _confidence(agent_result):
    resp = _build_response(agent_result=agent_result, clip_id="c", frame_paths=[],
                           video_metadata=None, processing_time_seconds=1.0, sport="basketball")
    return resp["verdict"]["confidence"]

def test_reconciliation_uses_tracking_confidence():
    high = _confidence(_agent_result(tracked_evidence={"tracking_confidence": 1.0}))
    low = _confidence(_agent_result(tracked_evidence={"tracking_confidence": 0.0}))
    none = _confidence(_agent_result())  # no tracked evidence -> legacy behavior
    assert high > none > low


# ---------------------------------------------------------------------------
# Diagnostics show when/how YOLO influenced the decision
# ---------------------------------------------------------------------------

def test_diagnostics_show_yolo_influence():
    dets = _dets(_controlled(1) + [_obj("person", 0.75, 0.5, 0.2, 0.6, track_id=2)],
                 [_obj("person", 0.55, 0.5, 0.3, 0.8, track_id=1), _obj("sports ball", 0.55, 0.7, 0.05, 0.05),
                  _obj("person", 0.8, 0.5, 0.2, 0.6, track_id=2)])
    evidence = summarize_tracked_evidence(dets)
    diag = _diagnostics_payload("anthropic_four_agent", "q", dets, detector="hybrid",
                                frames_analyzed=2, tracked_evidence=evidence)
    assert diag["yolo_influenced"] is True
    assert diag["tracked_evidence_present"] is True
    assert diag["defender_tracked"] is True
    assert diag["ball_trajectory_present"] is True
    assert 0.0 <= diag["tracking_confidence"] <= 1.0
    assert diag["possession_summary"] in ("dribbling", "gathered", "passing", "loose_ball")
    assert diag["influenced_reconciliation"] is True

def test_diagnostics_no_yolo_influence_for_claude_vision():
    diag = _diagnostics_payload("anthropic_four_agent", "q", None, detector="claude_vision", frames_analyzed=2)
    assert diag["yolo_influenced"] is False
    assert diag["tracked_evidence_present"] is False
    assert diag["tracking_confidence"] is None
    assert diag["defender_tracked"] is False
    assert diag["ball_trajectory_present"] is False
    assert diag["influenced_reconciliation"] is False
