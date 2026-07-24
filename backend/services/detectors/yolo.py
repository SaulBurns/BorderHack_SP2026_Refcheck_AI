"""YOLO detector (Phase 5; upgraded to YOLO26 in Sprint 18A).

Runs object detection over extracted frames and returns structured detections.
It does NOT derive sport-specific perception yet (no court geometry, defender
status, etc.) — that is a later phase. It emits a neutral baseline perception so
the pipeline remains runnable end-to-end and degrades to "inconclusive".

The registry key is kept as `yolov8` (a stable role identifier — see
`services/detectors/registry.py`); the concrete weights are configurable via
`YOLO_MODEL` and reported on `RawDetections.model`, so an upgrade is a config
change with no contract change.
"""

from __future__ import annotations

from pathlib import Path

from services.detectors.detection_models import DetectorResult, RawDetections
from services.detectors.frame_extraction import prepare_frames
from services.detectors.yolo_inference import YoloInferenceService


class YOLODetector:
    """Detector that produces normalized object detections via YOLOv8."""

    name = "yolov8"

    def __init__(self, inference_service: YoloInferenceService | None = None) -> None:
        self._service = inference_service or YoloInferenceService()

    def infer(self, frames: list[Path]) -> RawDetections:
        """Extract/validate frames and run inference -> normalized detections."""
        prepared = prepare_frames(frames)
        return self._service.infer([frame.path for frame in prepared])

    def detect(self, frames: list[Path], sport: str, original_call: str) -> DetectorResult:
        detections = self.infer(frames)
        return DetectorResult(
            perception=self._baseline_perception(detections, sport),
            detections=detections,
        )

    @staticmethod
    def _baseline_perception(detections: RawDetections, sport: str) -> dict:
        """Minimal, sport-agnostic perception payload (no sport-specific extraction)."""
        frame_count = len(detections.frames)
        object_count = sum(len(frame.objects) for frame in detections.frames)
        return {
            "sport": sport,
            "event_type": "unclear",
            "summary": (
                f"{detections.model} produced {object_count} object detections across "
                f"{frame_count} frames. Semantic perception (event type, player "
                "roles, geometry) is not yet derived from detections."
            ),
            "perception_confidence": 0.0,
            "visual_quality": "partial",
            "notes": (
                f"detector=yolov8; model={detections.model}; "
                f"frames={frame_count}; detections={object_count}"
            ),
        }
