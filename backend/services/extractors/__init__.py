"""Sport detail extraction layer (Phase 6).

Public API:
    SportDetailExtractor      - the extractor Protocol
    BasketballDetailExtractor - derives BasketballDetails from RawDetections
    HockeyDetailExtractor     - placeholder
    SoccerDetailExtractor     - placeholder
    LacrosseDetailExtractor   - placeholder
    EmptyDetailExtractor      - fallback for unconfigured sports
    ExtractorRegistry         - sport -> extractor class registry
    registry                  - the default registry instance
    get_extractor             - resolve an extractor by sport
"""

from services.extractors.base import SportDetailExtractor
from services.extractors.basketball import BasketballDetailExtractor
from services.extractors.placeholders import (
    EmptyDetailExtractor,
    HockeyDetailExtractor,
    LacrosseDetailExtractor,
    SoccerDetailExtractor,
)
from services.extractors.registry import ExtractorRegistry, get_extractor, registry

__all__ = [
    "SportDetailExtractor",
    "BasketballDetailExtractor",
    "HockeyDetailExtractor",
    "SoccerDetailExtractor",
    "LacrosseDetailExtractor",
    "EmptyDetailExtractor",
    "ExtractorRegistry",
    "registry",
    "get_extractor",
]
