"""Sport detail extractor registry.

Mirrors the detector registry. Unknown sports fall back to `EmptyDetailExtractor`
(never raises) — consistent with `perception_schema.get_sport_details_model`,
since sports are data-driven and normalized upstream.
"""

from __future__ import annotations

from services.extractors.base import SportDetailExtractor
from services.extractors.basketball import BasketballDetailExtractor
from services.extractors.placeholders import (
    EmptyDetailExtractor,
    HockeyDetailExtractor,
    LacrosseDetailExtractor,
    SoccerDetailExtractor,
)


class ExtractorRegistry:
    """Maps sport keys to their detail-extractor classes."""

    def __init__(self) -> None:
        self._extractors: dict[str, type[SportDetailExtractor]] = {}

    def register(self, sport: str, extractor_cls: type[SportDetailExtractor]) -> None:
        self._extractors[sport.lower().strip()] = extractor_cls

    def available(self) -> list[str]:
        return sorted(self._extractors)

    def create(self, sport: str | None = None) -> SportDetailExtractor:
        key = (sport or "").lower().strip()
        extractor_cls = self._extractors.get(key, EmptyDetailExtractor)
        return extractor_cls()


registry = ExtractorRegistry()
registry.register("basketball", BasketballDetailExtractor)
registry.register("hockey", HockeyDetailExtractor)
registry.register("soccer", SoccerDetailExtractor)
registry.register("lacrosse", LacrosseDetailExtractor)


def get_extractor(sport: str | None = None) -> SportDetailExtractor:
    """Resolve a sport detail extractor (unknown sports -> EmptyDetailExtractor)."""
    return registry.create(sport)
