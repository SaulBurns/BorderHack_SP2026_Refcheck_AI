"""Basketball sport plugin (Sprint 9).

Wires together everything basketball-specific the pipeline needs: the basketball
prompts, the basketball rule corpus, the `BasketballDetailExtractor`, the
tracked-evidence layer (`summarize_tracked_evidence`), and the NBA game-context
provider. `ai_analyzer` reaches all of this through the `Sport` interface, never
by checking `sport == "basketball"`.
"""

from __future__ import annotations

from typing import Any

from sports.base import Sport


class BasketballSport(Sport):
    name = "basketball"
    display_name = "Basketball"

    def perception_prompt(self) -> str:
        from sports.basketball.prompts import perception_prompt
        return perception_prompt()

    def adjudicator_prompt(self) -> str:
        from sports.basketball.prompts import adjudicator_prompt
        return adjudicator_prompt()

    def rule_records(self) -> dict:
        from rules.basketball_rules import BASKETBALL_RULES
        return BASKETBALL_RULES

    def detail_extractor(self) -> Any:
        from services.extractors.basketball import BasketballDetailExtractor
        return BasketballDetailExtractor()

    def details_model(self) -> Any:
        from services.perception_schema import BasketballDetails
        return BasketballDetails

    def sport_details(self, detections: Any, perception: dict) -> dict | None:
        if detections is None:
            return None
        return self.detail_extractor().extract(detections, perception).model_dump()

    def tracked_evidence(self, detections: Any) -> dict | None:
        if detections is None:
            return None
        from services.extractors.basketball_vision import summarize_tracked_evidence
        return summarize_tracked_evidence(detections)

    def metadata_provider(self) -> Any | None:
        from services.metadata.nba_provider import NBAMetadataProvider
        return NBAMetadataProvider()
