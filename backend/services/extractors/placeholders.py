"""Minimal placeholder sport detail extractors (Phase 6).

These return their sport's default details model and ignore detections for now
(no sport-specific derivation authored yet), consistent with the empty rule
datasets for these sports.

Soccer graduated out of this module in Sprint 10: its real extractor lives in
``sports/soccer/extractor.py`` and is registered directly.
"""

from __future__ import annotations

from services.detectors.detection_models import RawDetections
from services.perception_schema import (
    EmptySportDetails,
    HockeyDetails,
    LacrosseDetails,
)


class HockeyDetailExtractor:
    sport = "hockey"

    def extract(self, detections: RawDetections | None, perception: dict) -> HockeyDetails:
        return HockeyDetails()


class LacrosseDetailExtractor:
    sport = "lacrosse"

    def extract(self, detections: RawDetections | None, perception: dict) -> LacrosseDetails:
        return LacrosseDetails()


class EmptyDetailExtractor:
    """Fallback for sports without a configured extractor."""

    sport = ""

    def extract(self, detections: RawDetections | None, perception: dict) -> EmptySportDetails:
        return EmptySportDetails()
