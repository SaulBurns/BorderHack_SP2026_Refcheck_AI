"""Detector abstraction (Phase 4 of the sport-agnostic perception plan).

A `Detector` is the "eyes" of the pipeline: it turns extracted frames into a
perception payload. The default `ClaudeVisionDetector` wraps the existing
perception logic so behavior is unchanged; YOLOv8/hybrid detectors are
placeholders for later phases.

`detect()` returns a `DetectorResult` carrying a `perception` dict (the contract
the rest of the pipeline consumes) plus optional structured `detections`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from services.detectors.detection_models import DetectorResult


@runtime_checkable
class Detector(Protocol):
    """Protocol every detector implementation must satisfy.

    Attributes:
        name: Stable identifier used by the registry/config (e.g. "claude_vision").
    """

    name: str

    def detect(self, frames: list[Path], sport: str, original_call: str) -> DetectorResult:
        """Produce a detector result for the given frames.

        Args:
            frames: Ordered list of extracted frame image paths.
            sport: Normalized sport key (e.g. "basketball").
            original_call: The on-court call text, or "" if none.

        Returns:
            A DetectorResult whose `perception` dict is consumed by the
            downstream pipeline (and optional structured `detections`).
        """
        ...
