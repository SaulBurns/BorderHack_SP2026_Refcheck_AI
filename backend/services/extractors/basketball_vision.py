"""Basketball vision utilities (Phase 8).

Pure, framework-free functions that derive basketball-specific signals from a
detector's `RawDetections`: player tracking, ball tracking, ball-possession
transitions, movement-direction estimation, and primary-defender identification.
Possession, timeline, and defender identification share a single per-frame scan
(`_scan_controllers`) so the controlling player is computed only once per clip.

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


def track_ball(detections: RawDetections) -> list[tuple[int, BoundingBox]]:
    """Per-frame ball position (the primary ball) for every frame that has one.

    Sorted by frame index. Used to derive the ball's own movement direction —
    independent of any player — so the adjudicator can see where the ball went
    even when the ball itself is untracked (no stable track_id).
    """
    trajectory = [
        (frame.frame_index, _balls(frame)[0].bbox)
        for frame in detections.frames
        if _balls(frame)
    ]
    trajectory.sort(key=lambda item: item[0])
    return trajectory


def _scan_controllers(
    detections: RawDetections,
) -> list[tuple[FrameDetections, DetectionObject | None]]:
    """Single pass: for every ball-bearing frame, its controlling person (or None).

    This is the one place `_controlling_person` is evaluated per frame; possession,
    the possession timeline, and defender identification all derive from this list
    instead of re-scanning the detections. Frames without a ball are omitted (they
    never have a controller), matching the legacy per-function behavior.
    """
    return [(frame, _controlling_person(frame)) for frame in detections.frames if _balls(frame)]


def _possession_from_controllers(
    scan: list[tuple[FrameDetections, DetectionObject | None]],
) -> str | None:
    """offensive_control_status from a precomputed controller scan (None if no ball)."""
    if not scan:
        return None
    controllers = [controller for _, controller in scan]
    real_ids = [c.track_id for c in controllers if c is not None and c.track_id is not None]
    distinct = set(real_ids)
    if len(distinct) >= 2:
        return "passing"
    if real_ids and any(real_ids.count(tid) >= 2 for tid in distinct):
        return "dribbling"
    if any(c is not None for c in controllers):
        return "gathered"
    return "loose_ball"


def possession_status(detections: RawDetections) -> str | None:
    """Derive offensive_control_status from ball possession across frames.

    Returns None when no ball is detected (preserve perception value).
    """
    return _possession_from_controllers(_scan_controllers(detections))


def _direction_label(dx: float, dy: float) -> str:
    """Map an image-space displacement vector to a coarse movement label."""
    if math.hypot(dx, dy) < _MOVEMENT_EPSILON:
        return "stationary"
    if abs(dx) >= abs(dy):
        return "lateral"
    return "vertical" if dy < 0 else "forward"


def movement_direction(trajectory: list[tuple[int, BoundingBox]]) -> str | None:
    """Coarse image-space movement label from a track's net displacement."""
    if not trajectory or len(trajectory) < 2:
        return None
    _, first = trajectory[0]
    _, last = trajectory[-1]
    return _direction_label(last.x - first.x, last.y - first.y)


def trajectory_movement(trajectory: list[tuple[int, BoundingBox]]) -> str | None:
    """Temporally-grounded movement label using every frame in the trajectory.

    Averages box centers over the first vs. second half of the track (rather than
    only the endpoints) so a single jittery frame cannot flip the label. For a
    two-point track this reduces to the same net-displacement as
    ``movement_direction``.
    """
    if not trajectory or len(trajectory) < 2:
        return None
    midpoint = len(trajectory) / 2
    first_half = [box for _, box in trajectory[: math.ceil(midpoint)]]
    second_half = [box for _, box in trajectory[len(trajectory) // 2 :]]
    first_x = sum(b.x for b in first_half) / len(first_half)
    first_y = sum(b.y for b in first_half) / len(first_half)
    last_x = sum(b.x for b in second_half) / len(second_half)
    last_y = sum(b.y for b in second_half) / len(second_half)
    return _direction_label(last_x - first_x, last_y - first_y)


def _defender_from_controllers(
    scan: list[tuple[FrameDetections, DetectionObject | None]],
) -> tuple[int | None, bool]:
    """Nearest defender to the ball handler in the first controlled frame.

    Mirrors the legacy scan exactly: the first ball frame whose controller also
    has at least one other person present wins.
    """
    for frame, handler in scan:
        if handler is None:
            continue
        others = [o for o in _persons(frame) if o is not handler]
        if not others:
            continue
        nearest = min(others, key=lambda o: _center_distance(o.bbox, handler.bbox))
        return nearest.track_id, True
    return None, False


def identify_primary_defender(detections: RawDetections) -> tuple[int | None, bool]:
    """Find the defender nearest the ball handler in a controlled frame.

    Returns (defender_track_id, found). track_id may be None even when found
    (defender present but untracked).
    """
    return _defender_from_controllers(_scan_controllers(detections))


def analyze_basketball(detections: RawDetections) -> BasketballVisionFeatures:
    """Derive all available basketball features from detections (single scan)."""
    scan = _scan_controllers(detections)
    control = _possession_from_controllers(scan)
    defender_track_id, defender_found = _defender_from_controllers(scan)
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


def _timeline_from_controllers(
    scan: list[tuple[FrameDetections, DetectionObject | None]],
) -> list[dict]:
    """Per-frame ball-controller identity, derived from the shared scan."""
    return [
        {
            "frame_index": frame.frame_index,
            "controller_track_id": controller.track_id if controller is not None else None,
        }
        for frame, controller in scan
    ]


def _possession_changes(timeline: list[dict]) -> int:
    """Count transitions between distinct, tracked controllers across the timeline."""
    changes = 0
    previous: int | None = None
    seen_first = False
    for entry in timeline:
        controller = entry["controller_track_id"]
        if controller is None:
            continue
        if seen_first and controller != previous:
            changes += 1
        previous = controller
        seen_first = True
    return changes


def _dominant_controller(timeline: list[dict]) -> tuple[int | None, int]:
    """The most frequent tracked controller and how many frames it controlled."""
    counts: dict[int, int] = {}
    for entry in timeline:
        controller = entry["controller_track_id"]
        if controller is not None:
            counts[controller] = counts.get(controller, 0) + 1
    if not counts:
        return None, 0
    best = max(counts, key=lambda tid: counts[tid])
    return best, counts[best]


def _tracking_confidence(
    *,
    frames_total: int,
    frames_with_ball: int,
    players_tracked: int,
    ball_handler_track_id: int | None,
    defender_present: bool,
) -> float:
    """A deterministic [0, 1] signal for how well the clip could be tracked.

    Rewards ball coverage across frames, multiple tracked players, a stable
    offensive identity, and a located defender. Used to calibrate (not decide)
    final confidence — it never overrides the adjudicators.
    """
    ball_coverage = frames_with_ball / frames_total if frames_total else 0.0
    score = 0.4 * ball_coverage
    score += 0.3 if players_tracked >= 2 else (0.15 if players_tracked == 1 else 0.0)
    score += 0.2 if ball_handler_track_id is not None else 0.0
    score += 0.1 if defender_present else 0.0
    return round(max(0.0, min(1.0, score)), 3)


def summarize_tracked_evidence(detections: RawDetections | None) -> dict | None:
    """Rich, tracking-grounded evidence for the adjudicator (additive; basketball).

    Surfaces what the collapsed 3-field feature set drops: offensive/defender
    identities, a per-frame possession timeline, possession changes, temporally
    robust movement, coverage counts, and a tracking-confidence signal. Returns
    None when there is nothing to ground on, so callers add no prompt section.
    """
    if detections is None or not any(frame.objects for frame in detections.frames):
        return None

    frames_total = len(detections.frames)
    tracks = track_players(detections)
    players_tracked = len(tracks)

    # One scan over ball frames; possession, timeline, and defender all reuse it.
    scan = _scan_controllers(detections)
    frames_with_ball = len(scan)
    timeline = _timeline_from_controllers(scan)
    ball_handler_track_id, ball_handler_control_frames = _dominant_controller(timeline)
    defender_track_id, defender_present = _defender_from_controllers(scan)

    handler_trajectory = tracks.get(ball_handler_track_id) if ball_handler_track_id is not None else None
    defender_trajectory = tracks.get(defender_track_id) if defender_track_id is not None else None
    ball_trajectory = track_ball(detections)

    return {
        "frames_total": frames_total,
        "frames_with_ball": frames_with_ball,
        "players_tracked": players_tracked,
        "possession_summary": _possession_from_controllers(scan),
        "possession_timeline": timeline,
        "possession_changes": _possession_changes(timeline),
        "ball_handler_track_id": ball_handler_track_id,
        "ball_handler_control_frames": ball_handler_control_frames,
        "ball_handler_movement": trajectory_movement(handler_trajectory) if handler_trajectory else None,
        "defender_track_id": defender_track_id,
        "defender_present": defender_present,
        "defender_movement": trajectory_movement(defender_trajectory) if defender_trajectory else None,
        # Ball's own path across frames (independent of any player); None when the
        # ball appears in fewer than two frames.
        "ball_movement": trajectory_movement(ball_trajectory) if len(ball_trajectory) >= 2 else None,
        "tracking_confidence": _tracking_confidence(
            frames_total=frames_total,
            frames_with_ball=frames_with_ball,
            players_tracked=players_tracked,
            ball_handler_track_id=ball_handler_track_id,
            defender_present=defender_present,
        ),
    }
