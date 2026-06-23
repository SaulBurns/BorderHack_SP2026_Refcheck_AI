"""Detection result models (Phase 5 of the sport-agnostic perception plan).

These describe the *raw, sport-agnostic* output of an object detector (e.g.
YOLOv8). They are deliberately NOT part of the perception/sport_details schema —
mapping detections into sport-specific perception is a later phase.

`DetectorResult` is a lightweight dataclass (not Pydantic) so the `perception`
dict passes through unchanged (preserving exact ClaudeVisionDetector parity),
while the detection payload itself is validated by the Pydantic models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    """Axis-aligned box, normalized to [0, 1] as center-x/y + width/height."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)


class DetectionObject(BaseModel):
    """A single detected object in one frame."""

    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox
    track_id: int | None = None


class FrameDetections(BaseModel):
    """All detections for a single frame."""

    frame_index: int
    objects: list[DetectionObject] = Field(default_factory=list)


class RawDetections(BaseModel):
    """Per-frame detector output for a whole clip."""

    # protected_namespaces=() lets us keep the plan's `model` field name cleanly.
    model_config = ConfigDict(protected_namespaces=())

    model: str
    detector_version: str
    frames: list[FrameDetections] = Field(default_factory=list)


@dataclass(frozen=True)
class DetectorResult:
    """Unified detector return: a perception payload plus optional raw detections.

    `perception` is the dict consumed by the downstream pipeline (kept as a plain
    dict so it flows through unchanged). `detections` carries structured object
    detections when a detector produces them (None for pure Claude Vision).
    """

    perception: dict[str, Any]
    detections: RawDetections | None = None
