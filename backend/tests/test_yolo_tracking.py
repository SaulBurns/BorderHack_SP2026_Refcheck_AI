import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path

import pytest

from services.detectors.yolo_inference import RawBox, YoloInferenceService


# --- Fake ultralytics model (no ultralytics / torch needed) -------------------

class _FakeBox:
    def __init__(self, cls, xyxy, conf, track_id):
        self.cls = [cls]
        self.xyxy = [xyxy]
        self.conf = [conf]
        self.id = None if track_id is None else [track_id]


class _FakeResult:
    def __init__(self, boxes, names, shape):
        self.boxes = boxes
        self.names = names
        self.orig_shape = shape


class _FakeModel:
    def __init__(self, track_ids=(1, 2)):
        self.track_calls = []
        self.predict_calls = []
        self._track_ids = track_ids

    def _results(self):
        person = _FakeBox(0, (10, 10, 50, 90), 0.9, self._track_ids[0])
        ball = _FakeBox(32, (40, 40, 60, 60), 0.8, self._track_ids[1])
        return [_FakeResult([person, ball], {0: "person", 32: "sports ball"}, (100, 100))]

    def track(self, source, persist, tracker, conf, verbose):
        self.track_calls.append({"source": source, "persist": persist, "tracker": tracker})
        return self._results()

    def predict(self, source, conf, verbose):
        self.predict_calls.append(source)
        return self._results()


# ---------------------------------------------------------------------------
# Default path now uses tracking
# ---------------------------------------------------------------------------

def test_default_path_uses_tracking_not_predict():
    fake = _FakeModel()
    service = YoloInferenceService()
    service._loaded_model = fake  # skip ultralytics load
    service.infer([Path("f0.jpg"), Path("f1.jpg")])
    assert len(fake.track_calls) == 2
    assert fake.predict_calls == []

def test_tracking_persist_flag_sequence():
    fake = _FakeModel()
    service = YoloInferenceService()
    service._loaded_model = fake
    service.infer([Path("f0.jpg"), Path("f1.jpg"), Path("f2.jpg")])
    assert [c["persist"] for c in fake.track_calls] == [False, True, True]

def test_tracking_populates_track_ids():
    fake = _FakeModel(track_ids=(7, 8))
    service = YoloInferenceService()
    service._loaded_model = fake
    dets = service.infer([Path("f0.jpg")])
    objs = dets.frames[0].objects
    assert {o.label for o in objs} == {"person", "sports ball"}
    assert sorted(o.track_id for o in objs) == [7, 8]

def test_tracker_config_forwarded():
    fake = _FakeModel()
    service = YoloInferenceService(tracker="botsort.yaml")
    service._loaded_model = fake
    service.infer([Path("f0.jpg")])
    assert fake.track_calls[0]["tracker"] == "botsort.yaml"


# ---------------------------------------------------------------------------
# Graceful behavior when track ids are absent (tracking returned none)
# ---------------------------------------------------------------------------

def test_missing_track_ids_are_none():
    fake = _FakeModel(track_ids=(None, None))
    service = YoloInferenceService()
    service._loaded_model = fake
    dets = service.infer([Path("f0.jpg")])
    assert all(o.track_id is None for o in dets.frames[0].objects)


# ---------------------------------------------------------------------------
# Tracking can be disabled -> falls back to detection-only predict
# ---------------------------------------------------------------------------

def test_disable_tracking_uses_predict():
    fake = _FakeModel()
    service = YoloInferenceService(use_tracking=False)
    service._loaded_model = fake
    service.infer([Path("f0.jpg")])
    assert fake.predict_calls and fake.track_calls == []


# ---------------------------------------------------------------------------
# Injected predictor path is unchanged (per-frame, no tracking)
# ---------------------------------------------------------------------------

def test_injected_predictor_still_used_per_frame():
    def predictor(_frame):
        return [RawBox("person", 0.9, 0, 0, 10, 20, 100, 200, track_id=5)]

    dets = YoloInferenceService(predictor=predictor).infer([Path("a.jpg"), Path("b.jpg")])
    assert len(dets.frames) == 2
    assert dets.frames[0].objects[0].track_id == 5


# ---------------------------------------------------------------------------
# ultralytics unavailable -> explicit RuntimeError (degrades cleanly upstream)
# ---------------------------------------------------------------------------

def test_missing_ultralytics_raises_explicitly(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "ultralytics":
            raise ImportError("no ultralytics")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError) as exc:
        YoloInferenceService().infer([Path("a.jpg")])
    assert "ultralytics" in str(exc.value)
