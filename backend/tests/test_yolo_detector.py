import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path

import pytest
from pydantic import ValidationError

from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    DetectorResult,
    FrameDetections,
    RawDetections,
)
from services.detectors.hybrid import HybridDetector
from services.detectors.yolo import YOLODetector
from services.detectors.yolo_inference import (
    DETECTOR_VERSION,
    RawBox,
    YoloInferenceService,
    normalize_box,
)


# ---------------------------------------------------------------------------
# Detection model validation
# ---------------------------------------------------------------------------

def test_detection_object_confidence_bounds():
    bbox = BoundingBox(x=0.5, y=0.5, width=0.2, height=0.2)
    with pytest.raises(ValidationError):
        DetectionObject(label="person", confidence=1.5, bbox=bbox)

def test_bounding_box_rejects_out_of_range():
    with pytest.raises(ValidationError):
        BoundingBox(x=1.4, y=0.5, width=0.2, height=0.2)

def test_raw_detections_model_field_allowed():
    rd = RawDetections(model="yolov8n.pt", detector_version="0.1.0", frames=[])
    assert rd.model == "yolov8n.pt"

def test_detector_result_defaults():
    result = DetectorResult(perception={"sport": "basketball"})
    assert result.detections is None
    assert result.perception == {"sport": "basketball"}


# ---------------------------------------------------------------------------
# Inference result normalization
# ---------------------------------------------------------------------------

def test_normalize_box_center_and_size():
    box = RawBox("person", 0.9, x1=0, y1=0, x2=100, y2=200, image_width=200, image_height=400)
    obj = normalize_box(box)
    assert obj.label == "person"
    assert obj.confidence == 0.9
    assert obj.bbox.x == pytest.approx(0.25)
    assert obj.bbox.y == pytest.approx(0.25)
    assert obj.bbox.width == pytest.approx(0.5)
    assert obj.bbox.height == pytest.approx(0.5)

def test_normalize_box_handles_reversed_coordinates():
    box = RawBox("ball", 0.5, x1=200, y1=400, x2=0, y2=0, image_width=200, image_height=400)
    obj = normalize_box(box)
    assert obj.bbox.width == pytest.approx(1.0)
    assert obj.bbox.height == pytest.approx(1.0)

def test_normalize_box_clamps_confidence():
    box = RawBox("x", 2.0, 0, 0, 10, 10, 100, 100)
    assert normalize_box(box).confidence == 1.0

def test_normalize_box_preserves_track_id():
    box = RawBox("person", 0.8, 0, 0, 10, 10, 100, 100, track_id=7)
    assert normalize_box(box).track_id == 7


# ---------------------------------------------------------------------------
# YoloInferenceService with an injected predictor (no ultralytics needed)
# ---------------------------------------------------------------------------

def _two_person_predictor(_frame_path):
    return [
        RawBox("person", 0.9, 0, 0, 50, 100, 100, 200, track_id=1),
        RawBox("sports ball", 0.7, 40, 40, 60, 60, 100, 200, track_id=2),
    ]

def test_inference_service_produces_raw_detections():
    service = YoloInferenceService(model="yolov8n.pt", predictor=_two_person_predictor)
    detections = service.infer([Path("a.jpg"), Path("b.jpg")])
    assert isinstance(detections, RawDetections)
    assert detections.model == "yolov8n.pt"
    assert detections.detector_version == DETECTOR_VERSION
    assert [f.frame_index for f in detections.frames] == [0, 1]
    assert all(len(f.objects) == 2 for f in detections.frames)
    assert detections.frames[0].objects[0].label == "person"

def test_inference_service_empty_frames():
    service = YoloInferenceService(predictor=_two_person_predictor)
    assert service.infer([]).frames == []

def test_inference_service_missing_ultralytics_raises(monkeypatch):
    # No predictor injected and ultralytics unavailable -> clear error.
    service = YoloInferenceService()
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "ultralytics":
            raise ImportError("no module named ultralytics")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError) as exc:
        service.infer([Path("a.jpg")])
    assert "ultralytics" in str(exc.value)


# ---------------------------------------------------------------------------
# YOLODetector
# ---------------------------------------------------------------------------

def _make_frame_files(tmp_path, count):
    paths = []
    for i in range(count):
        p = tmp_path / f"frame_{i}.jpg"
        p.write_bytes(b"\xff\xd8\xff")
        paths.append(p)
    return paths

def test_yolo_detector_returns_detector_result(tmp_path):
    frames = _make_frame_files(tmp_path, 2)
    detector = YOLODetector(inference_service=YoloInferenceService(predictor=_two_person_predictor))
    result = detector.detect(frames, "basketball", "")
    assert isinstance(result, DetectorResult)
    assert isinstance(result.detections, RawDetections)
    assert len(result.detections.frames) == 2

def test_yolo_detector_baseline_perception_is_neutral(tmp_path):
    frames = _make_frame_files(tmp_path, 2)
    detector = YOLODetector(inference_service=YoloInferenceService(predictor=_two_person_predictor))
    perception = detector.detect(frames, "hockey", "").perception
    assert perception["sport"] == "hockey"
    assert perception["event_type"] == "unclear"
    assert perception["perception_confidence"] == 0.0
    # No sport-specific extraction yet (constraint).
    assert "defender_status" not in perception
    assert "court_geometry" not in perception

def test_yolo_detector_skips_missing_frames(tmp_path):
    frames = _make_frame_files(tmp_path, 1) + [tmp_path / "missing.jpg"]
    detector = YOLODetector(inference_service=YoloInferenceService(predictor=_two_person_predictor))
    result = detector.detect(frames, "basketball", "")
    assert len(result.detections.frames) == 1  # missing frame dropped

def test_yolo_detector_name():
    assert YOLODetector().name == "yolov8"


# ---------------------------------------------------------------------------
# HybridDetector — Claude perception metadata + YOLO detections (no fusion)
# ---------------------------------------------------------------------------

class _FakeClaude:
    def detect(self, frames, sport, original_call):
        return DetectorResult(
            perception={"sport": sport, "event_type": "possible_charge", "summary": "claude"},
            detections=None,
        )

class _FakeYolo:
    def infer(self, frames):
        return RawDetections(
            model="fake-yolo",
            detector_version="t",
            frames=[FrameDetections(frame_index=0, objects=[])],
        )

def test_hybrid_combines_claude_perception_with_yolo_detections():
    hybrid = HybridDetector(claude_detector=_FakeClaude(), yolo_detector=_FakeYolo())
    result = hybrid.detect(["frame.jpg"], "basketball", "")
    # Claude perception metadata preserved verbatim...
    assert result.perception["event_type"] == "possible_charge"
    assert result.perception["summary"] == "claude"
    # ...with YOLO detections attached.
    assert result.detections.model == "fake-yolo"
    assert len(result.detections.frames) == 1

def test_hybrid_detector_name():
    assert HybridDetector().name == "hybrid"
