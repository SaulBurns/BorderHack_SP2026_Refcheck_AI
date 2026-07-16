"""Sport plugins (Sprint 9 — multi-sport architecture).

Sports are plugins: each implements the `Sport` interface and is registered in
the `SportRegistry`. The four-agent pipeline resolves a sport with
`get_sport(sport)` and delegates all sport-specific behavior (prompts, rule
boosts, sport-details extraction, tracking, game context) to it, so
`ai_analyzer` never checks `sport == "basketball"`.

Layout::

    sports/
        base.py         # Sport interface (ABC)
        registry.py     # SportRegistry + get_sport()
        generic.py      # GenericSport fallback (unconfigured sports)
        basketball/     # first full implementation
"""

from sports.base import Sport
from sports.registry import SportRegistry, get_sport, registry

__all__ = ["Sport", "SportRegistry", "get_sport", "registry"]
