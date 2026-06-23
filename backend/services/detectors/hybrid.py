"""Hybrid detector (Phase 5, minimal).

Combines Claude Vision perception metadata with YOLOv8 detections. Full fusion
(YOLO priors feeding/correcting Claude reasoning) is NOT implemented yet — this
version simply attaches the structured detections to Claude's perception output.
"""

from __future__ import annotations

from pathlib import Path

from services.detectors.claude_vision import ClaudeVisionDetector
from services.detectors.detection_models import DetectorResult
from services.detectors.yolo import YOLODetector


class HybridDetector:
    """Claude perception metadata + YOLOv8 detections (no fusion yet)."""

    name = "hybrid"

    def __init__(
        self,
        claude_detector: ClaudeVisionDetector | None = None,
        yolo_detector: YOLODetector | None = None,
    ) -> None:
        self._claude = claude_detector or ClaudeVisionDetector()
        self._yolo = yolo_detector or YOLODetector()

    def detect(self, frames: list[Path], sport: str, original_call: str) -> DetectorResult:
        claude_result = self._claude.detect(frames, sport, original_call)
        detections = self._yolo.infer(frames)
        # Preserve Claude's perception verbatim; attach YOLO detections alongside.
        return DetectorResult(
            perception=claude_result.perception,
            detections=detections,
        )
