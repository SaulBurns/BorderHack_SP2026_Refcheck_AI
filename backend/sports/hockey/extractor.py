"""Hockey sport detail extractor (Sprint 11).

Derives ``HockeyDetails`` from the perception payload, mirroring
``sports/soccer/extractor.py``. It satisfies the shared ``SportDetailExtractor``
protocol and is registered in the extractor registry, so both the adjudication
signals and the frontend ``sport_details`` block resolve it via
``get_extractor("hockey")`` — exactly like basketball and soccer.

The hockey-specific perception fields (rink zone, goalie involvement, puck
possession, infraction candidate, boards involvement) are semantic judgements the
vision agent makes, not values derivable from raw bounding boxes, so extraction
reads them from the perception dict. The ``detections`` argument is accepted for
interface parity and future enrichment; when it is ``None`` (the default
Claude-vision path) the perception-derived block is returned unchanged.
"""

from __future__ import annotations

from services.detectors.detection_models import RawDetections
from services.perception_schema import HockeyDetails

# Defaults mirror the HockeyDetails model defaults so an absent perception field
# never produces an invalid or surprising value.
_DEFAULTS = {
    "zone": "unclear",
    "goalie_involved": False,
    "puck_possession": "unclear",
    "infraction_candidate": "unclear",
    "boards_involved": False,
}


class HockeyDetailExtractor:
    """Derives HockeyDetails from the perception payload."""

    sport = "hockey"

    def extract(self, detections: RawDetections | None, perception: dict) -> HockeyDetails:
        return self._from_perception(perception)

    @staticmethod
    def _from_perception(perception: dict | None) -> HockeyDetails:
        perception = perception or {}
        return HockeyDetails(
            zone=str(perception.get("zone") or _DEFAULTS["zone"]),
            goalie_involved=bool(perception.get("goalie_involved", _DEFAULTS["goalie_involved"])),
            puck_possession=str(perception.get("puck_possession") or _DEFAULTS["puck_possession"]),
            infraction_candidate=str(
                perception.get("infraction_candidate") or _DEFAULTS["infraction_candidate"]
            ),
            boards_involved=bool(perception.get("boards_involved", _DEFAULTS["boards_involved"])),
        )
