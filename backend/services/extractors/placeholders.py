"""Fallback sport detail extractor (Phase 6).

Every real sport now owns its detail extractor in its plugin package:
``sports/<sport>/extractor.py`` for basketball's split lives in
``services/extractors/basketball.py``, while soccer (Sprint 10), hockey
(Sprint 11), and lacrosse (Sprint 12) live under ``sports/<sport>/extractor.py``
and are registered directly.

Only the ``EmptyDetailExtractor`` fallback remains here — it yields a valid,
empty details block for any sport with no configured extractor, so an
unconfigured/unknown sport never crashes the response shape.
"""

from __future__ import annotations

from services.detectors.detection_models import RawDetections
from services.perception_schema import EmptySportDetails


class EmptyDetailExtractor:
    """Fallback for sports without a configured extractor."""

    sport = ""

    def extract(self, detections: RawDetections | None, perception: dict) -> EmptySportDetails:
        return EmptySportDetails()
