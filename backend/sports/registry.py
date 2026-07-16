"""Sport plugin registry (Sprint 9).

Maps a normalized sport name to its `Sport` plugin. An unregistered sport falls
back to a `GenericSport` carrying that name (Claude-only perception, no tracking
or game context), so the pipeline never has to know which sports are fully
implemented — it just calls `get_sport(sport)` and delegates.

Registering a new sport is one line here (plus its plugin under `sports/`); the
four-agent pipeline requires no changes.
"""

from __future__ import annotations

from sports.base import Sport
from sports.basketball import BasketballSport
from sports.generic import GenericSport


class SportRegistry:
    """Name → Sport plugin, with a name-carrying generic fallback."""

    def __init__(self) -> None:
        self._sports: dict[str, Sport] = {}

    def register(self, sport: Sport) -> None:
        self._sports[sport.name.lower().strip()] = sport

    def available(self) -> list[str]:
        return sorted(self._sports)

    def get(self, name: str | None) -> Sport:
        return self._sports.get((name or "").lower().strip()) or GenericSport(name or "")


# The single place sports are wired in.
registry = SportRegistry()
registry.register(BasketballSport())


def get_sport(name: str | None = None) -> Sport:
    """Resolve the Sport plugin for a sport name (GenericSport fallback)."""
    return registry.get(name)
