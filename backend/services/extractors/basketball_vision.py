"""Basketball vision utilities (Phase 8).

Pure, framework-free functions that derive basketball-specific signals from a
detector's `RawDetections`: player tracking, ball-possession transitions,
movement-direction estimation, and primary-defender identification.

Each function returns None / empty / a sentinel when the detections are
insufficient, so the caller can fall back to perception-derived values.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    FrameDetections,
    RawDetections,
)

_BALL_LABELS = {"sports ball", "basketball", "ball"}
_PERSON_LABELS = {"person", "player"}

# Normalized net displacement below which a tracked player is "stationary".
_MOVEMENT_EPSILON = 0.03


@dataclass(frozen=True)
class BasketballVisionFeatures:
    """Derived features; None means "could not determine, fall back to perception"."""

    offensive_control_status: str | None = None
    moving_direction: str | None = None
    primary_or_secondary: str | None = None


def _is_ball(obj: DetectionObject) -> bool:
    return obj.label.lower() in _BALL_LABELS


def _is_person(obj: DetectionObject) -> bool:
    return obj.label.lower() in _PERSON_LABELS


def _persons(frame: FrameDetections) -> list[DetectionObject]:
    return [o for o in frame.objects if _is_person(o)]


def _balls(frame: FrameDetections) -> list[DetectionObject]:
    return [o for o in frame.objects if _is_ball(o)]


def _center_inside(inner: BoundingBox, outer: BoundingBox) -> bool:
    return (
        (outer.x - outer.width / 2) <= inner.x <= (outer.x + outer.width / 2)
        and (outer.y - outer.height / 2) <= inner.y <= (outer.y + outer.height / 2)
    )


def _center_distance(a: BoundingBox, b: BoundingBox) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _controlling_person(frame: FrameDetections) -> DetectionObject | None:
    """The person whose box contains a ball center (nearest one), or None."""
    persons = _persons(frame)
    best: DetectionObject | None = None
    best_distance = math.inf
    for ball in _balls(frame):
        for person in persons:
            if _center_inside(ball.bbox, person.bbox):
                distance = _center_distance(ball.bbox, person.bbox)
                if distance < best_distance:
                    best_distance = distance
                    best = person
    return best


def track_players(detections: RawDetections) -> dict[int, list[tuple[int, BoundingBox]]]:
    """Group person detections into per-track trajectories, sorted by frame."""
    tracks: dict[int, list[tuple[int, BoundingBox]]] = {}
    for frame in detections.frames:
        for person in _persons(frame):
            if person.track_id is not None:
                tracks.setdefault(person.track_id, []).append((frame.frame_index, person.bbox))
    for trajectory in tracks.values():
        trajectory.sort(key=lambda item: item[0])
    return tracks


def possession_status(detections: RawDetections) -> str | None:
    """Derive offensive_control_status from ball possession across frames.

    Returns None when no ball is detected (preserve perception value).
    """
    saw_ball = False
    controlled_any = False
    controlled_track_ids: list[int | None] = []
    for frame in detections.frames:
        if not _balls(frame):
            continue
        saw_ball = True
        controller = _controlling_person(frame)
        if controller is not None:
            controlled_any = True
            controlled_track_ids.append(controller.track_id)

    if not saw_ball:
        return None

    real_ids = [tid for tid in controlled_track_ids if tid is not None]
    distinct = set(real_ids)
    if len(distinct) >= 2:
        return "passing"
    if real_ids and any(real_ids.count(tid) >= 2 for tid in distinct):
        return "dribbling"
    if controlled_any:
        return "gathered"
    return "loose_ball"


def movement_direction(trajectory: list[tuple[int, BoundingBox]]) -> str | None:
    """Coarse image-space movement label from a track's net displacement."""
    if not trajectory or len(trajectory) < 2:
        return None
    _, first = trajectory[0]
    _, last = trajectory[-1]
    dx = last.x - first.x
    dy = last.y - first.y
    if math.hypot(dx, dy) < _MOVEMENT_EPSILON:
        return "stationary"
    if abs(dx) >= abs(dy):
        return "lateral"
    return "vertical" if dy < 0 else "forward"


def identify_primary_defender(detections: RawDetections) -> tuple[int | None, bool]:
    """Find the defender nearest the ball handler in a controlled frame.

    Returns (defender_track_id, found). track_id may be None even when found
    (defender present but untracked).
    """
    for frame in detections.frames:
        handler = _controlling_person(frame)
        if handler is None:
            continue
        others = [o for o in _persons(frame) if o is not handler]
        if not others:
            continue
        nearest = min(others, key=lambda o: _center_distance(o.bbox, handler.bbox))
        return nearest.track_id, True
    return None, False


def analyze_basketball(detections: RawDetections) -> BasketballVisionFeatures:
    """Derive all available basketball features from detections."""
    control = possession_status(detections)
    defender_track_id, defender_found = identify_primary_defender(detections)
    primary = "primary" if defender_found else None

    moving = None
    if defender_track_id is not None:
        trajectory = track_players(detections).get(defender_track_id)
        if trajectory:
            moving = movement_direction(trajectory)

    return BasketballVisionFeatures(
        offensive_control_status=control,
        moving_direction=moving,
        primary_or_secondary=primary,
    )
