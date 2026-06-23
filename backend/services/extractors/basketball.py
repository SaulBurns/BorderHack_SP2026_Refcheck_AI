"""Basketball sport detail extractor (Phase 6).

When `RawDetections` are available it derives what it responsibly can from raw
boxes (currently `offensive_control_status` from ball-vs-player proximity) and
leaves geometry/defender judgements to the perception payload — deriving those
requires court keypoints, which is future work.

When detections are unavailable it reproduces exactly the `BasketballDetails`
that `_frontend_perception` builds today, preserving existing behavior.
"""

from __future__ import annotations

from services.detectors.detection_models import BoundingBox, FrameDetections, RawDetections
from services.perception_schema import BasketballDetails, CourtGeometry, DefenderStatus

_BALL_LABELS = {"sports ball", "basketball", "ball"}
_PERSON_LABELS = {"person", "player"}

# Defaults mirror _frontend_perception's legacy fallbacks (kept in sync via the
# backward-compat parity test in tests/test_extractors.py).
_DEFENDER_DEFAULTS = {
    "primary_or_secondary": "unclear",
    "legal_guarding_position": "unclear",
    "feet_set_before_contact": False,
    "moving_direction": "unclear",
    "inside_restricted_area": False,
}
_COURT_DEFAULTS = {
    "key_zone": "backcourt_or_unclear",
    "restricted_area_arc_visible": False,
    "defender_feet_visible": False,
    "basket_visible": False,
}


def _center_inside(inner: BoundingBox, outer: BoundingBox) -> bool:
    return (
        (outer.x - outer.width / 2) <= inner.x <= (outer.x + outer.width / 2)
        and (outer.y - outer.height / 2) <= inner.y <= (outer.y + outer.height / 2)
    )


def _frame_has_ball(frame: FrameDetections) -> bool:
    return any(obj.label.lower() in _BALL_LABELS for obj in frame.objects)


def _frame_ball_controlled(frame: FrameDetections) -> bool:
    persons = [o.bbox for o in frame.objects if o.label.lower() in _PERSON_LABELS]
    balls = [o.bbox for o in frame.objects if o.label.lower() in _BALL_LABELS]
    return any(_center_inside(ball, person) for ball in balls for person in persons)


class BasketballDetailExtractor:
    """Derives BasketballDetails from detections, falling back to perception."""

    sport = "basketball"

    def extract(self, detections: RawDetections | None, perception: dict) -> BasketballDetails:
        base = self._from_perception(perception)
        derived = self._offensive_control_from_detections(detections)
        if derived is not None:
            base = base.model_copy(update={"offensive_control_status": derived})
        return base

    @staticmethod
    def _from_perception(perception: dict | None) -> BasketballDetails:
        perception = perception or {}
        return BasketballDetails(
            offensive_control_status=str(perception.get("offensive_control_status") or "unclear"),
            defender_status=DefenderStatus(**(perception.get("defender_status") or _DEFENDER_DEFAULTS)),
            court_geometry=CourtGeometry(**(perception.get("court_geometry") or _COURT_DEFAULTS)),
        )

    @staticmethod
    def _offensive_control_from_detections(detections: RawDetections | None) -> str | None:
        """Derive offensive_control_status, or None when it can't be determined.

        Returns None (preserve the perception value) when no ball is detected, so
        Claude-provided context is never discarded in the hybrid path.
        """
        if detections is None:
            return None
        saw_ball = False
        controlled = False
        for frame in detections.frames:
            if _frame_has_ball(frame):
                saw_ball = True
                if _frame_ball_controlled(frame):
                    controlled = True
        if not saw_ball:
            return None
        return "gathered" if controlled else "loose_ball"
