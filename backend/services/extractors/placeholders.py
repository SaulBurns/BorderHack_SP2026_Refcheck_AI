"""Minimal placeholder sport detail extractors (Phase 6).

These return their sport's default details model and ignore detections for now
(no sport-specific derivation authored yet), consistent with the empty rule
datasets for these sports.

Soccer (Sprint 10) and hockey (Sprint 11) graduated out of this module: their
real extractors live in ``sports/soccer/extractor.py`` and
``sports/hockey/extractor.py`` and are registered directly. Only lacrosse remains
a placeholder here.
"""

from __future__ import annotations

from services.detectors.detection_models import RawDetections
from services.perception_schema import (
    EmptySportDetails,
    LacrosseDetails,
)


class LacrosseDetailExtractor:
    sport = "lacrosse"

    def extract(self, detections: RawDetections | None, perception: dict) -> LacrosseDetails:
        return LacrosseDetails()


class EmptyDetailExtractor:
    """Fallback for sports without a configured extractor."""

    sport = ""

    def extract(self, detections: RawDetections | None, perception: dict) -> EmptySportDetails:
        return EmptySportDetails()
