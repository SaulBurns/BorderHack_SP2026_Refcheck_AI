"""Sport detail extractor resolution — now registry-driven.

`get_extractor(sport)` delegates to the Sport plugin (`get_sport(sport).
detail_extractor()`), so the extractor for each sport is owned by its package and
adding a sport never edits this file. Unregistered sports resolve through
`GenericSport`, which returns `EmptyDetailExtractor` (never raises), preserving the
previous fallback behavior.
"""

from __future__ import annotations

from services.extractors.base import SportDetailExtractor


def get_extractor(sport: str | None = None) -> SportDetailExtractor:
    """Resolve a sport detail extractor (unknown sports -> EmptyDetailExtractor)."""
    from sports import get_sport
    return get_sport(sport).detail_extractor()
