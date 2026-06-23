"""Sport detail extraction (Phase 6 of the sport-agnostic perception plan).

A `SportDetailExtractor` converts a detector's `RawDetections` (and the perception
payload) into a sport-specific `SportDetails` model. This is the second registry
seam from the plan (§4): detectors are the "eyes", extractors turn raw detections
into sport-specific perception detail.

This layer is standalone — nothing in the runtime pipeline imports it yet, so the
current response behavior is unchanged. Extractors are designed so that when they
are wired in later, the no-detections path reproduces today's output exactly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from services.detectors.detection_models import RawDetections
from services.perception_schema import SportDetails


@runtime_checkable
class SportDetailExtractor(Protocol):
    """Protocol every sport detail extractor must satisfy.

    Attributes:
        sport: Stable sport key (e.g. "basketball").
    """

    sport: str

    def extract(self, detections: RawDetections | None, perception: dict) -> SportDetails:
        """Produce sport-specific details.

        Args:
            detections: Structured detections from a detector, or None when the
                detector did not produce any (e.g. pure Claude Vision).
            perception: The perception payload dict (used for fallback and for
                fields that cannot be derived from raw detections).

        Returns:
            A `SportDetails` subclass instance for this sport.
        """
        ...
