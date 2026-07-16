"""Lacrosse sport detail extractor (Sprint 12).

Derives ``LacrosseDetails`` from the perception payload, mirroring
``sports/soccer/extractor.py`` and ``sports/hockey/extractor.py``. It satisfies
the shared ``SportDetailExtractor`` protocol and is registered in the extractor
registry, so both the adjudication signals and the frontend ``sport_details``
block resolve it via ``get_extractor("lacrosse")``.

The lacrosse-specific perception fields (crease violation, cross-check, slashing,
ball-carrier status, warding) are semantic judgements the vision agent makes, not
values derivable from raw bounding boxes, so extraction reads them from the
perception dict. The ``detections`` argument is accepted for interface parity and
future enrichment; when it is ``None`` (the default Claude-vision path) the
perception-derived block is returned unchanged.
"""

from __future__ import annotations

from services.detectors.detection_models import RawDetections
from services.perception_schema import LacrosseDetails

# Defaults mirror the LacrosseDetails model defaults so an absent perception field
# never produces an invalid or surprising value.
_DEFAULTS = {
    "crease_violation": False,
    "cross_check": False,
    "slashing": False,
    "ball_carrier_status": "unclear",
    "warding": False,
}


class LacrosseDetailExtractor:
    """Derives LacrosseDetails from the perception payload."""

    sport = "lacrosse"

    def extract(self, detections: RawDetections | None, perception: dict) -> LacrosseDetails:
        return self._from_perception(perception)

    @staticmethod
    def _from_perception(perception: dict | None) -> LacrosseDetails:
        perception = perception or {}
        return LacrosseDetails(
            crease_violation=bool(perception.get("crease_violation", _DEFAULTS["crease_violation"])),
            cross_check=bool(perception.get("cross_check", _DEFAULTS["cross_check"])),
            slashing=bool(perception.get("slashing", _DEFAULTS["slashing"])),
            ball_carrier_status=str(
                perception.get("ball_carrier_status") or _DEFAULTS["ball_carrier_status"]
            ),
            warding=bool(perception.get("warding", _DEFAULTS["warding"])),
        )
