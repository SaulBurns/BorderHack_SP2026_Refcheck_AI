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

    def perception_prompt(self) -> str:
        from sports.soccer.prompts import perception_prompt
        return perception_prompt()

    def retrieval_prompt(self) -> str:
        from sports.soccer.prompts import retrieval_prompt
        return retrieval_prompt()

    def adjudicator_prompt(self) -> str:
        from sports.soccer.prompts import adjudicator_prompt
        return adjudicator_prompt()

    def boost_rule_score(self, rule_id: str, haystack: str) -> int:
        from sports.soccer.rules import boost_rule_score
        return boost_rule_score(rule_id, haystack)

    def sport_details(self, detections: Any, perception: dict) -> dict | None:
        if detections is None:
            return None
        from services.extractors import get_extractor
        return get_extractor("soccer").extract(detections, perception).model_dump()

    def tracked_evidence(self, detections: Any) -> dict | None:
        if detections is None:
            return None
        from sports.soccer.tracking import summarize_tracked_evidence
        return summarize_tracked_evidence(detections)

    def metadata_provider(self) -> Any | None:
        from sports.soccer.game_context import soccer_metadata_provider
        return soccer_metadata_provider()
