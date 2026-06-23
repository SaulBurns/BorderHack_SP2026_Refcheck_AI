"""Detector registry + configuration.

Selection order for `get_detector()`:
1. explicit `name` argument
2. the `DETECTOR` environment variable
3. `DEFAULT_DETECTOR` ("claude_vision")

Unknown names raise ValueError with the list of supported detectors.
"""

from __future__ import annotations

import os

from services.detectors.base import Detector
from services.detectors.claude_vision import ClaudeVisionDetector
from services.detectors.hybrid import HybridDetector
from services.detectors.yolo import YOLODetector

DEFAULT_DETECTOR = "claude_vision"
DETECTOR_ENV_VAR = "DETECTOR"


class DetectorRegistry:
    """Maps detector names to their implementation classes."""

    def __init__(self) -> None:
        self._detectors: dict[str, type[Detector]] = {}

    def register(self, name: str, detector_cls: type[Detector]) -> None:
        self._detectors[name.lower().strip()] = detector_cls

    def available(self) -> list[str]:
        return sorted(self._detectors)

    def create(self, name: str | None = None) -> Detector:
        key = (name or os.getenv(DETECTOR_ENV_VAR) or DEFAULT_DETECTOR).lower().strip()
        detector_cls = self._detectors.get(key)
        if detector_cls is None:
            raise ValueError(
                f"Unknown detector {key!r}. Supported detectors: "
                f"{', '.join(self.available())}."
            )
        return detector_cls()


registry = DetectorRegistry()
registry.register("claude_vision", ClaudeVisionDetector)
registry.register("yolov8", YOLODetector)
registry.register("hybrid", HybridDetector)


def get_detector(name: str | None = None) -> Detector:
    """Resolve a detector by name / DETECTOR env / default (claude_vision)."""
    return registry.create(name)
