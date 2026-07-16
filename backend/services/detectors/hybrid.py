"""Hybrid detector.

Combines Claude Vision perception (semantic understanding) with YOLOv8 tracked
detections (supporting evidence). Claude's perception is always preserved
verbatim; the detections are attached alongside so downstream agents can ground
their reasoning without replacing it.

Graceful degradation: YOLO is optional supporting evidence, so if inference
fails (e.g. ultralytics missing, a corrupt frame), the hybrid path keeps Claude's
perception and simply drops the tracking (`detections=None`) instead of failing
the whole analysis. The semantic four-agent pipeline still runs; diagnostics show
`detections_present=False` so the missing tracking is visible.
"""

from __future__ import annotations

from pathlib import Path

from services.detectors.claude_vision import ClaudeVisionDetector
from services.detectors.detection_models import DetectorResult
from services.detectors.yolo import YOLODetector


class HybridDetector:
    """Claude perception + YOLOv8 tracked detections as supporting evidence."""

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
        try:
            detections = self._yolo.infer(frames)
        except Exception:
            # YOLO is supporting evidence only — never let its failure discard the
            # semantic perception. Degrade to Claude-only (no tracking).
            detections = None
        # Preserve Claude's perception verbatim; attach YOLO detections when present.
        return DetectorResult(
            perception=claude_result.perception,
            detections=detections,
        )
