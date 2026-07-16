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
)
from services.registry import Registry
from sports.soccer.extractor import SoccerDetailExtractor


class ExtractorRegistry(Registry[SportDetailExtractor]):
    """Maps sport keys to detail-extractor classes (unknown -> EmptyDetailExtractor)."""

    def __init__(self) -> None:
        super().__init__("extractor", fallback=EmptyDetailExtractor)


registry = ExtractorRegistry()
registry.register("basketball", BasketballDetailExtractor)
registry.register("hockey", HockeyDetailExtractor)
registry.register("soccer", SoccerDetailExtractor)
registry.register("lacrosse", LacrosseDetailExtractor)


def get_extractor(sport: str | None = None) -> SportDetailExtractor:
    """Resolve a sport detail extractor (unknown sports -> EmptyDetailExtractor)."""
    return registry.create(sport)
