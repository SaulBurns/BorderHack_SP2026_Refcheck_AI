"""Basketball sport plugin (Sprint 9).

Wires together everything basketball-specific the pipeline needs: the basketball
prompts (from the shared catalog), the basketball rule-retrieval boosts, the
`BasketballDetailExtractor`, the tracked-evidence layer (`summarize_tracked_evidence`),
and the NBA game-context provider. `ai_analyzer` reaches all of this through the
`Sport` interface, never by checking `sport == "basketball"`.
"""

from __future__ import annotations

from typing import Any

from sports.base import Sport


class BasketballSport(Sport):
    name = "basketball"

    def perception_prompt(self) -> str:
        from services.analysis.prompts import _get_perception_prompt
        return _get_perception_prompt("basketball")

    def retrieval_prompt(self) -> str:
        from services.analysis.prompts import _get_retrieval_prompt
        return _get_retrieval_prompt("basketball")

    def adjudicator_prompt(self) -> str:
        from services.analysis.prompts import _get_adjudicator_prompt
        return _get_adjudicator_prompt("basketball")

    def boost_rule_score(self, rule_id: str, haystack: str) -> int:
        from sports.basketball.rules import boost_rule_score
        return boost_rule_score(rule_id, haystack)

    def sport_details(self, detections: Any, perception: dict) -> dict | None:
        if detections is None:
            return None
        from services.extractors import get_extractor
        return get_extractor("basketball").extract(detections, perception).model_dump()

    def tracked_evidence(self, detections: Any) -> dict | None:
        if detections is None:
            return None
        from services.extractors.basketball_vision import summarize_tracked_evidence
        return summarize_tracked_evidence(detections)

    def metadata_provider(self) -> Any | None:
        from services.metadata.nba_provider import NBAMetadataProvider
        return NBAMetadataProvider()
