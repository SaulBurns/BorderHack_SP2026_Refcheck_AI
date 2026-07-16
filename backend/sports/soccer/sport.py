"""Soccer sport plugin (Sprint 10 — first new sport).

Wires together everything soccer-specific the four-agent pipeline needs: the
soccer prompts, the soccer rule-retrieval boosts, the ``SoccerDetailExtractor``,
the soccer tracked-evidence layer, and the (currently absent) game-context
provider. ``ai_analyzer`` reaches all of this through the ``Sport`` interface,
never by checking ``sport == "soccer"``.

Mirrors ``sports/basketball/sport.py``: every import is lazy (inside the method)
so registering the plugin never triggers heavy imports or import cycles between
the ``sports`` package and ``services``.
"""

from __future__ import annotations

from typing import Any

from sports.base import Sport


class SoccerSport(Sport):
    name = "soccer"
    display_name = "Soccer"

    def perception_prompt(self) -> str:
        from sports.soccer.prompts import perception_prompt
        return perception_prompt()

    def retrieval_prompt(self) -> str:
        from sports.soccer.prompts import retrieval_prompt
        return retrieval_prompt()

    def adjudicator_prompt(self) -> str:
        from sports.soccer.prompts import adjudicator_prompt
        return adjudicator_prompt()

    def rule_records(self) -> dict:
        from rules.soccer_rules import SOCCER_RULES
        return SOCCER_RULES

    def boost_rule_score(self, rule_id: str, haystack: str) -> int:
        from sports.soccer.rules import boost_rule_score
        return boost_rule_score(rule_id, haystack)

    def detail_extractor(self) -> Any:
        from sports.soccer.extractor import SoccerDetailExtractor
        return SoccerDetailExtractor()

    def details_model(self) -> Any:
        from services.perception_schema import SoccerDetails
        return SoccerDetails

    def sport_details(self, detections: Any, perception: dict) -> dict | None:
        if detections is None:
            return None
        return self.detail_extractor().extract(detections, perception).model_dump()

    def tracked_evidence(self, detections: Any) -> dict | None:
        if detections is None:
            return None
        from sports.soccer.tracking import summarize_tracked_evidence
        return summarize_tracked_evidence(detections)

    def metadata_provider(self) -> Any | None:
        from sports.soccer.game_context import soccer_metadata_provider
        return soccer_metadata_provider()
