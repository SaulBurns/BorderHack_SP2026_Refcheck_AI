"""Sport detail extraction layer (Phase 6).

Public API:
    SportDetailExtractor      - the extractor Protocol
    BasketballDetailExtractor - derives BasketballDetails from RawDetections
    HockeyDetailExtractor     - derives HockeyDetails (sports/hockey/extractor.py)
    SoccerDetailExtractor     - derives SoccerDetails (sports/soccer/extractor.py)
    LacrosseDetailExtractor   - derives LacrosseDetails (sports/lacrosse/extractor.py)
    EmptyDetailExtractor      - fallback for unconfigured sports
    get_extractor             - resolve an extractor by sport (delegates to the plugin)

Extractor resolution is registry-driven: `get_extractor(sport)` delegates to
`get_sport(sport).detail_extractor()`, so there is no hardcoded sport->extractor
table here. The per-sport extractor classes are re-exported for convenience/tests.
"""

from services.extractors.base import SportDetailExtractor
from services.extractors.basketball import BasketballDetailExtractor
from services.extractors.placeholders import EmptyDetailExtractor
from services.extractors.registry import get_extractor
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
    "get_extractor",
]
