"""Hockey tracking evidence (Sprint 11).

Pure, framework-free functions that derive hockey-specific supporting evidence
from a detector's ``RawDetections``: which player is carrying the puck, a
per-frame possession timeline, possession changes, the puck's own movement, and a
coarse rush direction. The genuinely sport-agnostic primitives (player trajectory
grouping and temporally-robust movement labelling) are reused from
``services/extractors/basketball_vision.py`` rather than re-implemented — the only
hockey-specific piece is puck-label handling and the hockey framing of the summary.

Consistent with basketball and soccer, tracked detections are SUPPORTING EVIDENCE
ONLY: Claude Vision remains the semantic authority. This returns ``None`` when
there is nothing to ground on, so the adjudicator prompt gains no tracking section
and the default Claude-only path is unchanged.
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

# Hockey footage may label the puck "puck"/"hockey puck"; some detectors reuse the
# COCO "sports ball" class for the puck.
_PUCK_LABELS = {"puck", "hockey puck", "sports ball", "ball"}

# Fraction of the puck's net horizontal drift above which the rush has a clear
# left/right direction; below it we report "unclear".
_RUSH_EPSILON = 0.04


def _pucks(frame: FrameDetections) -> list[DetectionObject]:
    return [o for o in frame.objects if o.label.lower() in _PUCK_LABELS]


def _puck_carrier(frame: FrameDetections) -> DetectionObject | None:
    """The person whose box contains a puck center (nearest), or None."""
    persons = _persons(frame)
    best: DetectionObject | None = None
    best_distance = float("inf")
    for puck in _pucks(frame):
        for person in persons:
            if _center_inside(puck.bbox, person.bbox):
                distance = _center_distance(puck.bbox, person.bbox)
                if distance < best_distance:
                    best_distance = distance
                    best = person
    return best


def _scan_carriers(
    detections: RawDetections,
) -> list[tuple[FrameDetections, DetectionObject | None]]:
    """Single pass: for every puck-bearing frame, its puck carrier (or None)."""
    return [(frame, _puck_carrier(frame)) for frame in detections.frames if _pucks(frame)]


def track_puck(detections: RawDetections) -> list[tuple[int, BoundingBox]]:
    """Per-frame puck position (the primary puck), sorted by frame index."""
    trajectory = [
        (frame.frame_index, _pucks(frame)[0].bbox)
        for frame in detections.frames
        if _pucks(frame)
    ]
    trajectory.sort(key=lambda item: item[0])
    return trajectory


def _possession_summary(
    scan: list[tuple[FrameDetections, DetectionObject | None]],
) -> str | None:
    """Coarse possession state from a precomputed carrier scan (None if no puck)."""
    if not scan:
        return None
    carriers = [carrier for _, carrier in scan]
    real_ids = [c.track_id for c in carriers if c is not None and c.track_id is not None]
    distinct = set(real_ids)
    if len(distinct) >= 2:
        return "contested"
    if any(c is not None for c in carriers):
        return "in_possession"
    return "loose_puck"


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


def _rush_direction(puck_trajectory: list[tuple[int, BoundingBox]]) -> str:
    """Coarse left/right rush direction from the puck's net horizontal drift."""
    if len(puck_trajectory) < 2:
        return "unclear"
    _, first = puck_trajectory[0]
    _, last = puck_trajectory[-1]
    dx = last.x - first.x
    if abs(dx) < _RUSH_EPSILON:
        return "unclear"
    return "left_to_right" if dx > 0 else "right_to_left"


def _tracking_confidence(
    *,
    frames_total: int,
    frames_with_puck: int,
    players_tracked: int,
    carrier_present: bool,
) -> float:
    """A deterministic [0, 1] signal for how well the clip could be tracked.

    Rewards puck coverage across frames, multiple tracked players, and a located
    puck carrier. Used to calibrate (not decide) final confidence — it never
    overrides the adjudicators.
    """
    puck_coverage = frames_with_puck / frames_total if frames_total else 0.0
    score = 0.4 * puck_coverage
    score += 0.3 if players_tracked >= 2 else (0.15 if players_tracked == 1 else 0.0)
    score += 0.3 if carrier_present else 0.0
    return round(max(0.0, min(1.0, score)), 3)


def summarize_tracked_evidence(detections: RawDetections | None) -> dict | None:
    """Tracking-grounded hockey evidence for the adjudicator (additive).

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
    frames_with_puck = len(scan)
    timeline = _timeline(scan)
    carrier_present = any(entry["carrier_track_id"] is not None for entry in timeline)
    puck_trajectory = track_puck(detections)

    return {
        "frames_total": frames_total,
        "frames_with_puck": frames_with_puck,
        "players_tracked": players_tracked,
        "possession_summary": _possession_summary(scan),
        "possession_timeline": timeline,
        "possession_changes": _possession_changes(timeline),
        "puck_carrier_present": carrier_present,
        "puck_movement": trajectory_movement(puck_trajectory) if len(puck_trajectory) >= 2 else None,
        "rush_direction": _rush_direction(puck_trajectory),
        "tracking_confidence": _tracking_confidence(
            frames_total=frames_total,
            frames_with_puck=frames_with_puck,
            players_tracked=players_tracked,
            carrier_present=carrier_present,
        ),
    }
