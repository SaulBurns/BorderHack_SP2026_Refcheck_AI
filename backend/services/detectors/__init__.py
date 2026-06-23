"""Detector abstraction layer.

Public API:
    Detector             - the detector Protocol
    DetectorResult       - perception dict + optional structured detections
    ClaudeVisionDetector - default, behavior-preserving detector
    YOLODetector         - YOLOv8 object detection (Phase 5)
    HybridDetector       - Claude perception + YOLO detections (Phase 5, no fusion)
    DetectorRegistry     - name -> detector class registry
    registry             - the default registry instance
    get_detector         - resolve a detector by name / DETECTOR env / default
    DEFAULT_DETECTOR     - "claude_vision"

Detection models:
    BoundingBox, DetectionObject, FrameDetections, RawDetections
"""

from services.detectors.base import Detector
from services.detectors.claude_vision import ClaudeVisionDetector
from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    DetectorResult,
    FrameDetections,
    RawDetections,
)
from services.detectors.hybrid import HybridDetector
from services.detectors.registry import (
    DEFAULT_DETECTOR,
    DETECTOR_ENV_VAR,
    DetectorRegistry,
    get_detector,
    registry,
)
from services.detectors.yolo import YOLODetector

__all__ = [
    "Detector",
    "DetectorResult",
    "ClaudeVisionDetector",
    "YOLODetector",
    "HybridDetector",
    "DetectorRegistry",
    "registry",
    "get_detector",
    "DEFAULT_DETECTOR",
    "DETECTOR_ENV_VAR",
    "BoundingBox",
    "DetectionObject",
    "FrameDetections",
    "RawDetections",
]
