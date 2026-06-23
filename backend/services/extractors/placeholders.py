"""Minimal placeholder sport detail extractors (Phase 6).

These return their sport's default details model and ignore detections for now
(no sport-specific derivation authored yet), consistent with the empty rule
datasets for these sports.
"""

from __future__ import annotations

from services.detectors.detection_models import RawDetections
from services.perception_schema import (
    EmptySportDetails,
    HockeyDetails,
    LacrosseDetails,
    SoccerDetails,
)


class HockeyDetailExtractor:
    sport = "hockey"

    def extract(self, detections: RawDetections | None, perception: dict) -> HockeyDetails:
        return HockeyDetails()


class SoccerDetailExtractor:
    sport = "soccer"

    def extract(self, detections: RawDetections | None, perception: dict) -> SoccerDetails:
        return SoccerDetails()


class LacrosseDetailExtractor:
    sport = "lacrosse"

    def extract(self, detections: RawDetections | None, perception: dict) -> LacrosseDetails:
        return LacrosseDetails()


class EmptyDetailExtractor:
    """Fallback for sports without a configured extractor."""

    sport = ""

    def extract(self, detections: RawDetections | None, perception: dict) -> EmptySportDetails:
        return EmptySportDetails()
