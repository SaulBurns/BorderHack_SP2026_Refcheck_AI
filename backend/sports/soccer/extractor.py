"""Soccer sport detail extractor (Sprint 10).

Derives ``SoccerDetails`` from the perception payload, mirroring
``services/extractors/basketball.py``. It satisfies the shared
``SportDetailExtractor`` protocol and is registered in the extractor registry, so
both the adjudication signals and the frontend ``sport_details`` block resolve it
via ``get_extractor("soccer")`` — exactly like basketball.

The soccer-specific perception fields (field third, penalty-area location,
offside/handball relevance, foul direction) are semantic judgements the vision
agent makes, not values derivable from raw bounding boxes, so extraction reads
them from the perception dict. The ``detections`` argument is accepted for
interface parity and future enrichment; when it is ``None`` (the default
Claude-vision path) the perception-derived block is returned unchanged.
"""

from __future__ import annotations

from services.detectors.detection_models import RawDetections
from services.perception_schema import SoccerDetails

# Defaults mirror the SoccerDetails model defaults so an absent perception field
# never produces an invalid or surprising value.
_DEFAULTS = {
    "field_third": "unclear",
    "in_penalty_area": False,
    "offside_relevant": False,
    "last_defender": False,
    "handball_candidate": False,
    "foul_direction": "unclear",
}


class SoccerDetailExtractor:
    """Derives SoccerDetails from the perception payload."""

    sport = "soccer"

    def extract(self, detections: RawDetections | None, perception: dict) -> SoccerDetails:
        return self._from_perception(perception)

    @staticmethod
    def _from_perception(perception: dict | None) -> SoccerDetails:
        perception = perception or {}
        return SoccerDetails(
            field_third=str(perception.get("field_third") or _DEFAULTS["field_third"]),
            in_penalty_area=bool(perception.get("in_penalty_area", _DEFAULTS["in_penalty_area"])),
            offside_relevant=bool(perception.get("offside_relevant", _DEFAULTS["offside_relevant"])),
            last_defender=bool(perception.get("last_defender", _DEFAULTS["last_defender"])),
            handball_candidate=bool(perception.get("handball_candidate", _DEFAULTS["handball_candidate"])),
            foul_direction=str(perception.get("foul_direction") or _DEFAULTS["foul_direction"]),
        )
