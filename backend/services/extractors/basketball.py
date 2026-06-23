"""Basketball sport detail extractor (Phase 6-8).

Derives BasketballDetails from a detector's RawDetections, falling back to the
perception payload for any field that cannot be determined from detections.

Phase 8 adds vision-derived enrichment (ball possession transitions, primary
defender identification, movement direction) via `basketball_vision`. Every
derived field is applied only when available, so the no-detections path and the
insufficient-detection path reproduce existing behavior exactly.
"""

from __future__ import annotations

from services.detectors.detection_models import RawDetections
from services.extractors.basketball_vision import analyze_basketball
from services.perception_schema import BasketballDetails, CourtGeometry, DefenderStatus

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


class BasketballDetailExtractor:
    """Derives BasketballDetails from detections, falling back to perception."""

    sport = "basketball"

    def extract(self, detections: RawDetections | None, perception: dict) -> BasketballDetails:
        base = self._from_perception(perception)
        if detections is None:
            return base

        features = analyze_basketball(detections)

        updates: dict = {}
        if features.offensive_control_status is not None:
            updates["offensive_control_status"] = features.offensive_control_status

        defender_updates: dict = {}
        if features.primary_or_secondary is not None:
            defender_updates["primary_or_secondary"] = features.primary_or_secondary
        if features.moving_direction is not None:
            defender_updates["moving_direction"] = features.moving_direction
        if defender_updates:
            updates["defender_status"] = base.defender_status.model_copy(update=defender_updates)

        return base.model_copy(update=updates) if updates else base

    @staticmethod
    def _from_perception(perception: dict | None) -> BasketballDetails:
        perception = perception or {}
        return BasketballDetails(
            offensive_control_status=str(perception.get("offensive_control_status") or "unclear"),
            defender_status=DefenderStatus(**(perception.get("defender_status") or _DEFENDER_DEFAULTS)),
            court_geometry=CourtGeometry(**(perception.get("court_geometry") or _COURT_DEFAULTS)),
        )
