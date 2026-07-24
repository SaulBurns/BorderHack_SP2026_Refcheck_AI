"""YOLOv8 inference service (Phase 5).

`ultralytics` is an optional, heavy dependency (it pulls in torch), so it is
imported lazily and only when the default predictor actually runs. Tests and the
rest of the app never need it: a `predictor` callable can be injected, and the
pixel->normalized conversion (`normalize_box`) is a pure function.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from services import config
from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    FrameDetections,
    RawDetections,
)

# Sprint 18A — bumped for the YOLO26 upgrade (was 0.2.0 on YOLOv8). Reported on
# every RawDetections so a stored/diagnosed detection payload records which
# detector build produced it.
DETECTOR_VERSION = "0.3.0"
# Canonical defaults live in config (env-overridable); re-exported for back-compat.
DEFAULT_MODEL = config.DEFAULT_YOLO_MODEL
DEFAULT_CONFIDENCE = config.DEFAULT_YOLO_CONFIDENCE
DEFAULT_TRACKER = config.DEFAULT_YOLO_TRACKER


@dataclass(frozen=True)
class RawBox:
    """A detection straight off the model, in pixel coordinates (xyxy)."""

    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    image_width: int
    image_height: int
    track_id: int | None = None


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def normalize_box(box: RawBox) -> DetectionObject:
    """Convert a pixel-space xyxy box into a normalized center+size detection."""
    width = max(box.image_width, 1)
    height = max(box.image_height, 1)
    x1, x2 = sorted((box.x1, box.x2))
    y1, y2 = sorted((box.y1, box.y2))

    center_x = ((x1 + x2) / 2) / width
    center_y = ((y1 + y2) / 2) / height
    box_width = (x2 - x1) / width
    box_height = (y2 - y1) / height

    return DetectionObject(
        label=box.label,
        confidence=_clamp(box.confidence),
        bbox=BoundingBox(
            x=_clamp(center_x),
            y=_clamp(center_y),
            width=_clamp(box_width),
            height=_clamp(box_height),
        ),
        track_id=box.track_id,
    )


# A predictor turns one frame path into raw (pixel-space) boxes.
Predictor = Callable[[Path], list[RawBox]]


class YoloInferenceService:
    """Runs YOLOv8 over frames and normalizes the output.

    Args:
        model: Weights identifier passed to ultralytics (e.g. "yolov8n.pt").
        predictor: Optional injected predictor (used by tests / custom backends).
            When None, a lazily-loaded ultralytics model is used.
        confidence: Minimum confidence threshold for the default predictor.
    """

    def __init__(
        self,
        model: str | None = None,
        predictor: Predictor | None = None,
        confidence: float | None = None,
        use_tracking: bool | None = None,
        tracker: str | None = None,
    ) -> None:
        # Sprint 18A — every setting resolves through config: an explicit arg wins,
        # else the YOLO_* env var, else the default (YOLO26). Passing None (the new
        # default) picks up env/config; existing callers passing explicit values are
        # unchanged.
        self._model = config.resolved_yolo_model(model)
        self._predictor = predictor
        self._confidence = config.resolved_yolo_confidence(confidence)
        # Tracking (model.track with persist) gives stable track_id's across the
        # clip's frames; detection-only (model.predict) leaves track_id None.
        self._use_tracking = config.resolved_yolo_tracking(use_tracking)
        self._tracker = config.resolved_yolo_tracker(tracker)
        self._loaded_model = None  # cached ultralytics model

    def _load_model(self):
        if self._loaded_model is None:
            try:
                from ultralytics import YOLO
            except ImportError as exc:  # pragma: no cover - exercised only in prod
                raise RuntimeError(
                    "The 'ultralytics' package is required for YOLOv8 inference. "
                    "Install it (pip install ultralytics) or inject a predictor."
                ) from exc
            self._loaded_model = YOLO(self._model)
        return self._loaded_model

    @staticmethod
    def _parse_results(results) -> list[RawBox]:
        boxes: list[RawBox] = []
        for result in results:
            names = result.names
            height, width = result.orig_shape
            for detection in result.boxes:
                class_id = int(detection.cls[0])
                x1, y1, x2, y2 = (float(value) for value in detection.xyxy[0])
                track_id = int(detection.id[0]) if detection.id is not None else None
                boxes.append(
                    RawBox(
                        label=names.get(class_id, str(class_id)),
                        confidence=float(detection.conf[0]),
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                        image_width=int(width),
                        image_height=int(height),
                        track_id=track_id,
                    )
                )
        return boxes

    def _default_predictor(self, frame_path: Path, persist: bool) -> list[RawBox]:
        """Run the loaded ultralytics model on one frame.

        Uses `model.track(persist=...)` so track_id's stay stable across the
        clip's frames; falls back to `model.predict` when tracking is disabled.
        `persist=True` keeps the tracker state between successive frames.
        """
        model = self._load_model()
        if self._use_tracking:
            results = model.track(
                source=str(frame_path),
                persist=persist,
                tracker=self._tracker,
                conf=self._confidence,
                verbose=False,
            )
        else:  # pragma: no cover - detection-only fallback
            results = model.predict(source=str(frame_path), conf=self._confidence, verbose=False)
        return self._parse_results(results)

    def infer(self, frame_paths: list[Path]) -> RawDetections:
        """Run inference over ordered frame paths and return normalized detections.

        For the default (ultralytics) path, frames are processed in order with the
        tracker persisting across them. An injected `predictor` is called per frame
        unchanged (tests / custom backends).
        """
        frames: list[FrameDetections] = []
        for index, frame_path in enumerate(frame_paths):
            path = Path(frame_path)
            if self._predictor is not None:
                raw_boxes = self._predictor(path)
            else:
                raw_boxes = self._default_predictor(path, persist=index > 0)
            objects = [normalize_box(box) for box in raw_boxes]
            frames.append(FrameDetections(frame_index=index, objects=objects))
        return RawDetections(
            model=self._model,
            detector_version=DETECTOR_VERSION,
            frames=frames,
        )
