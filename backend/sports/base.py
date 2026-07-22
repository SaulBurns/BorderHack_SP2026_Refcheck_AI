"""Sport plugin interface (Sprint 9 — multi-sport architecture).

A `Sport` owns everything the three-agent pipeline needs to know that is
sport-specific: the perception/adjudication prompts, the rule corpus,
sport-details extraction, tracking-evidence derivation, and game-context
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
    """One sport's behavior, plugged into the pipeline via the SportRegistry.

    A ``Sport`` is fully self-contained: it owns its prompts, rule corpus,
    detail extraction, detail schema, tracking evidence, and game context. The
    generic pipeline and lookup functions (`get_rules_for_sport`, `_get_*_prompt`,
    `get_extractor`, `get_sport_details_model`) resolve a plugin with
    `get_sport(sport)` and delegate, so adding a sport requires only a
    `sports/<sport>/` package plus one `SportRegistry.register(...)` call — no other
    backend file changes.
    """

    #: Normalized sport key (e.g. "basketball").
    name: str

    #: Human-readable label (e.g. "Basketball"). Defaults to a title-cased name.
    display_name: str = ""

    # -- prompts (sport-specific perception + adjudication) -----------------

    @abstractmethod
    def perception_prompt(self) -> str:
        """System prompt for the perception agent."""

    @abstractmethod
    def adjudicator_prompt(self) -> str:
        """System prompt for both adjudicators (framing is appended per-agent)."""

    # -- rule corpus --------------------------------------------------------

    @abstractmethod
    def rule_records(self) -> dict:
        """The sport's rulebook corpus.

        A mapping of ``rule_key -> {"call_type", "rule_applied", "summary", ...}``.
        The pipeline injects this corpus in full into the adjudicators (Sprint 16A
        removed the retrieval stage). Return ``{}`` for a sport with no authored
        rules (GenericSport fallback).
        """

    # -- sport-details extraction + schema ----------------------------------

    @abstractmethod
    def detail_extractor(self) -> Any:
        """The sport's detail extractor (a `SportDetailExtractor`).

        Resolved by the generic `get_extractor(sport)` seam. Return an
        `EmptyDetailExtractor` for a sport with no authored extractor.
        """

    @abstractmethod
    def details_model(self) -> Any:
        """The sport's `SportDetails` subclass.

        Resolved by the generic `get_sport_details_model(sport)` seam. Return
        `EmptySportDetails` for a sport with no authored schema.
        """

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
