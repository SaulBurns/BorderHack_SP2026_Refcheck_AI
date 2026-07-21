"""Lacrosse sport plugin (Sprint 12 — fourth sport).

Wires together everything lacrosse-specific the three-agent pipeline needs: the
lacrosse prompts, the lacrosse rule corpus, the
``LacrosseDetailExtractor``, the lacrosse tracked-evidence layer, and the
(currently absent) game-context provider. ``ai_analyzer`` reaches all of this
through the ``Sport`` interface, never by checking ``sport == "lacrosse"``.

Mirrors ``sports/soccer/sport.py`` and ``sports/hockey/sport.py``: every import is
lazy (inside the method) so registering the plugin never triggers heavy imports or
import cycles between the ``sports`` package and ``services``.
"""

from __future__ import annotations

from typing import Any

from sports.base import Sport


class LacrosseSport(Sport):
    name = "lacrosse"
    display_name = "Lacrosse"

    def perception_prompt(self) -> str:
        from sports.lacrosse.prompts import perception_prompt
        return perception_prompt()

    def adjudicator_prompt(self) -> str:
        from sports.lacrosse.prompts import adjudicator_prompt
        return adjudicator_prompt()

    def rule_records(self) -> dict:
        from rules.lacrosse_rules import LACROSSE_RULES
        return LACROSSE_RULES

    def detail_extractor(self) -> Any:
        from sports.lacrosse.extractor import LacrosseDetailExtractor
        return LacrosseDetailExtractor()

    def details_model(self) -> Any:
        from services.perception_schema import LacrosseDetails
        return LacrosseDetails

    def sport_details(self, detections: Any, perception: dict) -> dict | None:
        if detections is None:
            return None
        return self.detail_extractor().extract(detections, perception).model_dump()

    def tracked_evidence(self, detections: Any) -> dict | None:
        if detections is None:
            return None
        from sports.lacrosse.tracking import summarize_tracked_evidence
        return summarize_tracked_evidence(detections)

    def metadata_provider(self) -> Any | None:
        from sports.lacrosse.game_context import lacrosse_metadata_provider
        return lacrosse_metadata_provider()
