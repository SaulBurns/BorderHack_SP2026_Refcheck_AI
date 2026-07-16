"""Detector registry + configuration.

Selection order for `get_detector()`:
1. explicit `name` argument
2. the `DETECTOR` environment variable
3. `DEFAULT_DETECTOR` ("claude_vision")

Unknown names raise ValueError with the list of supported detectors.
"""

from __future__ import annotations

from services import config
from services.detectors.base import Detector
from services.detectors.claude_vision import ClaudeVisionDetector
from services.detectors.hybrid import HybridDetector
from services.detectors.yolo import YOLODetector
from services.registry import Registry

# Re-exported for backward compatibility; canonical values live in config.
DEFAULT_DETECTOR = config.DEFAULT_DETECTOR
DETECTOR_ENV_VAR = config.DETECTOR_ENV


class DetectorRegistry(Registry[Detector]):
    """Maps detector names to their implementation classes (raises on unknown)."""

    def __init__(self) -> None:
        super().__init__("detector")


registry = DetectorRegistry()
registry.register("claude_vision", ClaudeVisionDetector)
registry.register("yolov8", YOLODetector)
registry.register("hybrid", HybridDetector)


def get_detector(name: str | None = None) -> Detector:
    """Resolve a detector by name / DETECTOR env / default (claude_vision)."""
    return registry.create(config.resolved_detector(name))
