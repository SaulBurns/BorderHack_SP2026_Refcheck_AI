"""Hockey sport plugin (Sprint 11 — second new sport).

Wires together everything hockey-specific the three-agent pipeline needs: the
hockey prompts, the hockey rule corpus, the ``HockeyDetailExtractor``,
the hockey tracked-evidence layer, and the (currently absent) game-context
provider. ``ai_analyzer`` reaches all of this through the ``Sport`` interface,
never by checking ``sport == "hockey"``.

Mirrors ``sports/soccer/sport.py``: every import is lazy (inside the method) so
registering the plugin never triggers heavy imports or import cycles between the
``sports`` package and ``services``.
"""

from __future__ import annotations

from typing import Any

from sports.base import Sport


class HockeySport(Sport):
    name = "hockey"
    display_name = "Hockey"

    def perception_prompt(self) -> str:
        from sports.hockey.prompts import perception_prompt
        return perception_prompt()

    def adjudicator_prompt(self) -> str:
        from sports.hockey.prompts import adjudicator_prompt
        return adjudicator_prompt()

    def rule_records(self) -> dict:
        from rules.hockey_rules import HOCKEY_RULES
        return HOCKEY_RULES

    def detail_extractor(self) -> Any:
        from sports.hockey.extractor import HockeyDetailExtractor
        return HockeyDetailExtractor()

    def details_model(self) -> Any:
        from services.perception_schema import HockeyDetails
        return HockeyDetails

    def sport_details(self, detections: Any, perception: dict) -> dict | None:
        if detections is None:
            return None
        return self.detail_extractor().extract(detections, perception).model_dump()

    def tracked_evidence(self, detections: Any) -> dict | None:
        if detections is None:
            return None
        from sports.hockey.tracking import summarize_tracked_evidence
        return summarize_tracked_evidence(detections)

    def metadata_provider(self) -> Any | None:
        from sports.hockey.game_context import hockey_metadata_provider
        return hockey_metadata_provider()
