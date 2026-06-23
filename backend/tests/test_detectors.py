import os
import sys

# Run from backend/ so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.detectors import (
    DEFAULT_DETECTOR,
    ClaudeVisionDetector,
    Detector,
    DetectorRegistry,
    HybridDetector,
    YOLODetector,
    get_detector,
    registry,
)


# ---------------------------------------------------------------------------
# Registry resolution
# ---------------------------------------------------------------------------

def test_get_detector_claude_vision():
    assert isinstance(get_detector("claude_vision"), ClaudeVisionDetector)

def test_get_detector_yolov8():
    assert isinstance(get_detector("yolov8"), YOLODetector)

def test_get_detector_hybrid():
    assert isinstance(get_detector("hybrid"), HybridDetector)

def test_get_detector_is_case_insensitive():
    assert isinstance(get_detector("Claude_Vision"), ClaudeVisionDetector)
    assert isinstance(get_detector("  YOLOV8 "), YOLODetector)

def test_get_detector_returns_fresh_instances():
    assert get_detector("claude_vision") is not get_detector("claude_vision")

def test_available_lists_all_three():
    assert registry.available() == ["claude_vision", "hybrid", "yolov8"]


# ---------------------------------------------------------------------------
# Default selection + env configuration
# ---------------------------------------------------------------------------

def test_default_constant_is_claude_vision():
    assert DEFAULT_DETECTOR == "claude_vision"

def test_default_detector_when_unset(monkeypatch):
    monkeypatch.delenv("DETECTOR", raising=False)
    assert isinstance(get_detector(), ClaudeVisionDetector)
    assert isinstance(get_detector(None), ClaudeVisionDetector)

def test_env_var_overrides_default(monkeypatch):
    monkeypatch.setenv("DETECTOR", "yolov8")
    assert isinstance(get_detector(), YOLODetector)

def test_explicit_name_overrides_env(monkeypatch):
    monkeypatch.setenv("DETECTOR", "yolov8")
    assert isinstance(get_detector("claude_vision"), ClaudeVisionDetector)


# ---------------------------------------------------------------------------
# Unsupported detector handling
# ---------------------------------------------------------------------------

def test_unknown_detector_raises_value_error():
    with pytest.raises(ValueError) as exc:
        get_detector("magic_eyes")
    message = str(exc.value)
    assert "magic_eyes" in message
    assert "claude_vision" in message  # lists supported detectors

def test_unknown_env_detector_raises(monkeypatch):
    monkeypatch.setenv("DETECTOR", "nope")
    with pytest.raises(ValueError):
        get_detector()


# ---------------------------------------------------------------------------
# Detector names + protocol conformance
# ---------------------------------------------------------------------------

def test_detector_names():
    assert ClaudeVisionDetector().name == "claude_vision"
    assert YOLODetector().name == "yolov8"
    assert HybridDetector().name == "hybrid"

@pytest.mark.parametrize("detector_cls", [ClaudeVisionDetector, YOLODetector, HybridDetector])
def test_detectors_satisfy_protocol(detector_cls):
    assert isinstance(detector_cls(), Detector)


# ---------------------------------------------------------------------------
# Custom registry behavior
# ---------------------------------------------------------------------------

def test_custom_registry_register_and_create():
    reg = DetectorRegistry()
    reg.register("claude_vision", ClaudeVisionDetector)
    assert isinstance(reg.create("claude_vision"), ClaudeVisionDetector)
    assert reg.available() == ["claude_vision"]

def test_custom_registry_unknown_raises():
    reg = DetectorRegistry()
    with pytest.raises(ValueError):
        reg.create("anything")


# ---------------------------------------------------------------------------
# ClaudeVisionDetector parity with the existing perception flow
# ---------------------------------------------------------------------------

def test_claude_vision_detector_delegates_to_perception_agent(monkeypatch):
    import services.ai_analyzer as ai

    captured = {}
    sentinel = {"sport": "basketball", "event_type": "possible_blocking_foul", "summary": "x"}

    def fake_perception_agent(frame_paths, original_call, sport):
        captured["args"] = (frame_paths, original_call, sport)
        return sentinel

    monkeypatch.setattr(ai, "_perception_agent", fake_perception_agent)

    frames = ["f1.jpg", "f2.jpg"]
    result = ClaudeVisionDetector().detect(frames, "basketball", "blocking foul")

    # Wraps the perception output verbatim (identity preserved), no detections...
    assert result.perception is sentinel
    assert result.detections is None
    # ...and maps detect(frames, sport, original_call) -> _perception_agent(frames, original_call, sport).
    assert captured["args"] == (frames, "blocking foul", "basketball")

def test_default_detector_routes_perception_through_claude_vision(monkeypatch):
    """End-to-end: the pipeline's perception call resolves to ClaudeVisionDetector."""
    import services.ai_analyzer as ai

    monkeypatch.delenv("DETECTOR", raising=False)
    monkeypatch.setattr(ai, "_perception_agent", lambda f, oc, s: {"sport": s, "routed": True})

    # get_detector() (no arg) must produce the behavior-preserving detector.
    result = ai.get_detector().detect(["frame.jpg"], "basketball", "")
    assert result.perception == {"sport": "basketball", "routed": True}
    assert result.detections is None
