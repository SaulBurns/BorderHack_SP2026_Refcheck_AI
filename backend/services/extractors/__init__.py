"""Sport detail extraction layer (Phase 6).

Public API:
    SportDetailExtractor      - the extractor Protocol
    BasketballDetailExtractor - derives BasketballDetails from RawDetections
    HockeyDetailExtractor     - derives HockeyDetails (sports/hockey/extractor.py)
    SoccerDetailExtractor     - derives SoccerDetails (sports/soccer/extractor.py)
    LacrosseDetailExtractor   - derives LacrosseDetails (sports/lacrosse/extractor.py)
    EmptyDetailExtractor      - fallback for unconfigured sports
    ExtractorRegistry         - sport -> extractor class registry
    registry                  - the default registry instance
    get_extractor             - resolve an extractor by sport
"""

from services.extractors.base import SportDetailExtractor
from services.extractors.basketball import BasketballDetailExtractor
from services.extractors.placeholders import EmptyDetailExtractor
from services.extractors.registry import ExtractorRegistry, get_extractor, registry
from sports.hockey.extractor import HockeyDetailExtractor
from sports.lacrosse.extractor import LacrosseDetailExtractor
from sports.soccer.extractor import SoccerDetailExtractor

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
