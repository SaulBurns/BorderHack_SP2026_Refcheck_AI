"""Sport plugin interface (Sprint 9 — multi-sport architecture).

A `Sport` owns everything the four-agent pipeline needs to know that is
sport-specific: the perception/retrieval/adjudication prompts, rule-retrieval
boosts, sport-details extraction, tracking-evidence derivation, and game-context
metadata. `ai_analyzer` stays sport-agnostic — it resolves a sport via
`SportRegistry.get(sport)` and delegates, so adding a new sport never touches
core pipeline code.

Implementations delegate to the existing shared building blocks (the prompt
catalog, the extractor registry, the metadata providers, the basketball vision
helpers) rather than reimplementing them, so behavior is identical and the
plugin is the single place a sport's wiring lives.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Sport(ABC):
    """One sport's behavior, plugged into the pipeline via the SportRegistry."""

    #: Normalized sport key (e.g. "basketball"). Matches rules.sport_config keys.
    name: str

    # -- prompts (sport-specific perception + adjudication) -----------------

    @abstractmethod
    def perception_prompt(self) -> str:
        """System prompt for the perception agent."""

    @abstractmethod
    def retrieval_prompt(self) -> str:
        """System prompt for the retrieval-query agent."""

    @abstractmethod
    def adjudicator_prompt(self) -> str:
        """System prompt for both adjudicators (framing is appended per-agent)."""

    # -- rule retrieval -----------------------------------------------------

    @abstractmethod
    def boost_rule_score(self, rule_id: str, haystack: str) -> int:
        """Sport-specific keyword boost for a candidate rule during ranking.

        Returns 0 for sports without tuned retrieval, leaving the generic
        keyword score untouched.
        """

    # -- sport-details extraction -------------------------------------------

    @abstractmethod
    def sport_details(self, detections: Any, perception: dict) -> dict | None:
        """Structured sport signals for adjudication, or None when unavailable."""

    # -- tracking helpers ---------------------------------------------------

    @abstractmethod
    def tracked_evidence(self, detections: Any) -> dict | None:
        """Tracking-grounded evidence (identities, possession, movement) for the
        adjudicators, or None when the sport has no tracking layer / no detections.
        """

    # -- game context -------------------------------------------------------

    @abstractmethod
    def metadata_provider(self) -> Any | None:
        """The game-context metadata provider for this sport, or None."""
