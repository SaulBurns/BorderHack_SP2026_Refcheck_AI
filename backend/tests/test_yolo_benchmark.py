"""Sprint 18A — YOLO detection & tracking benchmark metrics.

Covers the pure IoU / precision-recall-F1 detection scoring and the tracking-quality
metrics (ID switches, purity, matched ratio) used to measure the YOLO upgrade
before and after, plus the config-driven default-weights upgrade.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services import config
from services.detectors.benchmark import (
    detection_metrics,
    iou,
    match_frame,
    tracking_metrics,
)
from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    FrameDetections,
    RawDetections,
)


def _obj(label, x, y, w, h, conf=0.9, track_id=None):
    return DetectionObject(label=label, confidence=conf,
                           bbox=BoundingBox(x=x, y=y, width=w, height=h), track_id=track_id)


def _dets(frames):
    return RawDetections(model="test", detector_version="t",
                         frames=[FrameDetections(frame_index=i, objects=o) for i, o in enumerate(frames)])


# ---------------------------------------------------------------------------
# IoU + matching
# ---------------------------------------------------------------------------

def test_iou_identical_boxes_is_one():
    b = BoundingBox(x=0.5, y=0.5, width=0.2, height=0.2)
    assert iou(b, b) == pytest.approx(1.0)


def test_iou_disjoint_boxes_is_zero():
    a = BoundingBox(x=0.1, y=0.1, width=0.1, height=0.1)
    b = BoundingBox(x=0.9, y=0.9, width=0.1, height=0.1)
    assert iou(a, b) == 0.0


def test_iou_half_overlap():
    # Two 0.2-wide, 0.2-tall boxes offset so they overlap half in x, full in y.
    a = BoundingBox(x=0.4, y=0.5, width=0.2, height=0.2)
    b = BoundingBox(x=0.5, y=0.5, width=0.2, height=0.2)
    # intersection 0.1*0.2=0.02; union 0.04+0.04-0.02=0.06 -> 1/3
    assert iou(a, b) == pytest.approx(1 / 3)


def test_match_frame_respects_label():
    pred = [_obj("person", 0.5, 0.5, 0.2, 0.2)]
    truth = [_obj("ball", 0.5, 0.5, 0.2, 0.2)]
    assert match_frame(pred, truth) == []  # same box, different label -> no match
    assert len(match_frame(pred, truth, match_label=False)) == 1


# ---------------------------------------------------------------------------
# Detection accuracy
# ---------------------------------------------------------------------------

def test_detection_metrics_perfect():
    d = _dets([[_obj("person", 0.5, 0.5, 0.2, 0.2)]])
    m = detection_metrics(d, d)
    assert m.true_positives == 1 and m.false_positives == 0 and m.false_negatives == 0
    assert m.precision == 1.0 and m.recall == 1.0 and m.f1 == 1.0


def test_detection_metrics_false_positive_and_negative():
    truth = _dets([[_obj("person", 0.2, 0.2, 0.1, 0.1), _obj("ball", 0.8, 0.8, 0.1, 0.1)]])
    # predicts the person (TP) + a spurious box (FP), misses the ball (FN).
    pred = _dets([[_obj("person", 0.2, 0.2, 0.1, 0.1), _obj("person", 0.5, 0.5, 0.1, 0.1)]])
    m = detection_metrics(pred, truth)
    assert m.true_positives == 1 and m.false_positives == 1 and m.false_negatives == 1
    assert m.precision == 0.5 and m.recall == 0.5 and m.f1 == 0.5


def test_detection_metrics_missing_frame_counts_as_misses():
    truth = _dets([[_obj("person", 0.5, 0.5, 0.2, 0.2)], [_obj("person", 0.5, 0.5, 0.2, 0.2)]])
    pred = _dets([[_obj("person", 0.5, 0.5, 0.2, 0.2)]])  # only frame 0
    m = detection_metrics(pred, truth)
    assert m.true_positives == 1 and m.false_negatives == 1  # frame 1 unmatched


# ---------------------------------------------------------------------------
# Tracking quality
# ---------------------------------------------------------------------------

def test_tracking_metrics_stable_track_no_switches():
    # One GT track (id 1) across 3 frames; pred consistently gives track_id 10.
    frames_truth = [[_obj("person", 0.5, 0.5, 0.2, 0.2, track_id=1)] for _ in range(3)]
    frames_pred = [[_obj("person", 0.5, 0.5, 0.2, 0.2, track_id=10)] for _ in range(3)]
    m = tracking_metrics(_dets(frames_pred), _dets(frames_truth))
    assert m.gt_tracks == 1 and m.pred_tracks == 1
    assert m.id_switches == 0
    assert m.track_purity == 1.0
    assert m.matched_ratio == 1.0


def test_tracking_metrics_counts_id_switch():
    # Pred flips the track id on frame 2 -> one ID switch, purity 2/3.
    frames_truth = [[_obj("person", 0.5, 0.5, 0.2, 0.2, track_id=1)] for _ in range(3)]
    frames_pred = [
        [_obj("person", 0.5, 0.5, 0.2, 0.2, track_id=10)],
        [_obj("person", 0.5, 0.5, 0.2, 0.2, track_id=10)],
        [_obj("person", 0.5, 0.5, 0.2, 0.2, track_id=11)],
    ]
    m = tracking_metrics(_dets(frames_pred), _dets(frames_truth))
    assert m.id_switches == 1
    assert m.track_purity == pytest.approx(2 / 3, abs=1e-4)  # rounded to 4dp


def test_tracking_metrics_matched_ratio_drops_on_missed_frame():
    frames_truth = [[_obj("person", 0.5, 0.5, 0.2, 0.2, track_id=1)] for _ in range(4)]
    frames_pred = [
        [_obj("person", 0.5, 0.5, 0.2, 0.2, track_id=10)],
        [],  # missed detection
        [_obj("person", 0.5, 0.5, 0.2, 0.2, track_id=10)],
        [_obj("person", 0.5, 0.5, 0.2, 0.2, track_id=10)],
    ]
    m = tracking_metrics(_dets(frames_pred), _dets(frames_truth))
    assert m.matched_ratio == pytest.approx(3 / 4)
    assert m.id_switches == 0  # the gap doesn't count as a switch


# ---------------------------------------------------------------------------
# The upgrade: default weights + version
# ---------------------------------------------------------------------------

def test_default_weights_upgraded_to_yolo26(monkeypatch):
    for k in ("YOLO_MODEL", "YOLO_CONFIDENCE", "YOLO_TRACKER", "YOLO_TRACKING"):
        monkeypatch.delenv(k, raising=False)
    assert config.resolved_yolo_model() == "yolo26n.pt"
    assert config.DEFAULT_YOLO_MODEL == "yolo26n.pt"


def test_yolo_config_env_overrides(monkeypatch):
    monkeypatch.setenv("YOLO_MODEL", "yolo11n.pt")
    monkeypatch.setenv("YOLO_CONFIDENCE", "0.4")
    monkeypatch.setenv("YOLO_TRACKING", "0")
    assert config.resolved_yolo_model() == "yolo11n.pt"
    assert config.resolved_yolo_confidence() == 0.4
    assert config.resolved_yolo_tracking() is False
    # explicit arg beats env
    assert config.resolved_yolo_model("yolov8n.pt") == "yolov8n.pt"
