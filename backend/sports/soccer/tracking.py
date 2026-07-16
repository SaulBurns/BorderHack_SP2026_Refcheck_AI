"""Soccer tracking evidence (Sprint 10).

Pure, framework-free functions that derive soccer-specific supporting evidence
from a detector's ``RawDetections``: which player is in possession, a per-frame
possession timeline, possession changes, the ball's own movement, and a coarse
attacking direction. The low-level primitives that are genuinely sport-agnostic
(player trajectory grouping and temporally-robust movement labelling) are reused
from ``services/extractors/basketball_vision.py`` rather than re-implemented — the
only soccer-specific piece is ball-label handling (soccer footage often labels
the ball "soccer ball") and the soccer framing of the summary.

Consistent with basketball, tracked detections are SUPPORTING EVIDENCE ONLY:
Claude Vision remains the semantic authority. This returns ``None`` when there is
nothing to ground on, so the adjudicator prompt gains no tracking section and the
default Claude-only path is unchanged.
"""

from __future__ import annotations

from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    FrameDetections,
    RawDetections,
)
from services.extractors.basketball_vision import (
    _center_distance,
    _center_inside,
    _persons,
    track_players,
    trajectory_movement,
)

# Soccer footage may label the ball "soccer ball" (COCO uses "sports ball").
_BALL_LABELS = {"sports ball", "soccer ball", "football", "ball"}

# Fraction of tracked players' net horizontal drift above which attack has a
# clear left/right direction; below it we report "unclear".
_ATTACK_EPSILON = 0.04


def _balls(frame: FrameDetections) -> list[DetectionObject]:
    return [o for o in frame.objects if o.label.lower() in _BALL_LABELS]


def _ball_carrier(frame: FrameDetections) -> DetectionObject | None:
    """The person whose box contains a ball center (nearest), or None."""
    persons = _persons(frame)
    best: DetectionObject | None = None
    best_distance = float("inf")
    for ball in _balls(frame):
        for person in persons:
            if _center_inside(ball.bbox, person.bbox):
                distance = _center_distance(ball.bbox, person.bbox)
                if distance < best_distance:
                    best_distance = distance
                    best = person
    return best


def _scan_carriers(
    detections: RawDetections,
) -> list[tuple[FrameDetections, DetectionObject | None]]:
    """Single pass: for every ball-bearing frame, its ball carrier (or None)."""
    return [(frame, _ball_carrier(frame)) for frame in detections.frames if _balls(frame)]


def track_ball(detections: RawDetections) -> list[tuple[int, BoundingBox]]:
    """Per-frame ball position (the primary ball), sorted by frame index."""
    trajectory = [
        (frame.frame_index, _balls(frame)[0].bbox)
        for frame in detections.frames
        if _balls(frame)
    ]
    trajectory.sort(key=lambda item: item[0])
    return trajectory


def _possession_summary(
    scan: list[tuple[FrameDetections, DetectionObject | None]],
) -> str | None:
    """Coarse possession state from a precomputed carrier scan (None if no ball)."""
    if not scan:
        return None
    carriers = [carrier for _, carrier in scan]
    real_ids = [c.track_id for c in carriers if c is not None and c.track_id is not None]
    distinct = set(real_ids)
    if len(distinct) >= 2:
        return "contested"
    if any(c is not None for c in carriers):
        return "in_possession"
    return "loose_ball"


def _timeline(
    scan: list[tuple[FrameDetections, DetectionObject | None]],
) -> list[dict]:
    return [
        {
            "frame_index": frame.frame_index,
            "carrier_track_id": carrier.track_id if carrier is not None else None,
        }
        for frame, carrier in scan
    ]


def _possession_changes(timeline: list[dict]) -> int:
    """Count transitions between distinct, tracked carriers across the timeline."""
    changes = 0
    previous: int | None = None
    seen_first = False
    for entry in timeline:
        carrier = entry["carrier_track_id"]
        if carrier is None:
            continue
        if seen_first and carrier != previous:
            changes += 1
        previous = carrier
        seen_first = True
    return changes


def _attacking_direction(ball_trajectory: list[tuple[int, BoundingBox]]) -> str:
    """Coarse left/right attacking direction from the ball's net horizontal drift."""
    if len(ball_trajectory) < 2:
        return "unclear"
    _, first = ball_trajectory[0]
    _, last = ball_trajectory[-1]
    dx = last.x - first.x
    if abs(dx) < _ATTACK_EPSILON:
        return "unclear"
    return "left_to_right" if dx > 0 else "right_to_left"


def _tracking_confidence(
    *,
    frames_total: int,
    frames_with_ball: int,
    players_tracked: int,
    carrier_present: bool,
) -> float:
    """A deterministic [0, 1] signal for how well the clip could be tracked.

    Rewards ball coverage across frames, multiple tracked players, and a located
    ball carrier. Used to calibrate (not decide) final confidence — it never
    overrides the adjudicators.
    """
    ball_coverage = frames_with_ball / frames_total if frames_total else 0.0
    score = 0.4 * ball_coverage
    score += 0.3 if players_tracked >= 2 else (0.15 if players_tracked == 1 else 0.0)
    score += 0.3 if carrier_present else 0.0
    return round(max(0.0, min(1.0, score)), 3)


def summarize_tracked_evidence(detections: RawDetections | None) -> dict | None:
    """Tracking-grounded soccer evidence for the adjudicator (additive).

    Returns None when there is nothing to ground on (no detections / empty
    frames), so callers add no prompt section and the Claude-only path is
    unchanged.
    """
    if detections is None or not any(frame.objects for frame in detections.frames):
        return None

    frames_total = len(detections.frames)
    tracks = track_players(detections)
    players_tracked = len(tracks)

    scan = _scan_carriers(detections)
    frames_with_ball = len(scan)
    timeline = _timeline(scan)
    carrier_present = any(entry["carrier_track_id"] is not None for entry in timeline)
    ball_trajectory = track_ball(detections)

    return {
        "frames_total": frames_total,
        "frames_with_ball": frames_with_ball,
        "players_tracked": players_tracked,
        "possession_summary": _possession_summary(scan),
        "possession_timeline": timeline,
        "possession_changes": _possession_changes(timeline),
        "ball_carrier_present": carrier_present,
        "ball_movement": trajectory_movement(ball_trajectory) if len(ball_trajectory) >= 2 else None,
        "attacking_direction": _attacking_direction(ball_trajectory),
        "tracking_confidence": _tracking_confidence(
            frames_total=frames_total,
            frames_with_ball=frames_with_ball,
            players_tracked=players_tracked,
            carrier_present=carrier_present,
        ),
    }
