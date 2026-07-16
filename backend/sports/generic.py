"""Generic sport plugin — the fallback for sports without a full implementation.

Reproduces the pre-plugin behavior for any unconfigured sport (hockey, soccer,
lacrosse, or anything else): Claude-only perception via the shared prompt
catalog's stub prompts, no rule boosts, no tracking evidence, and no game
context. The placeholder extractor still yields a valid (empty) sport-details
block, so the response shape is unchanged.
"""

from __future__ import annotations

from typing import Any

from sports.base import Sport


class GenericSport(Sport):
    """Behavior for a sport that has no dedicated plugin yet."""

    def __init__(self, name: str) -> None:
        self.name = (name or "").lower().strip()

    def perception_prompt(self) -> str:
        from services.analysis.prompts import _get_perception_prompt
        return _get_perception_prompt(self.name)

    def retrieval_prompt(self) -> str:
        from services.analysis.prompts import _get_retrieval_prompt
        return _get_retrieval_prompt(self.name)

    def adjudicator_prompt(self) -> str:
        from services.analysis.prompts import _get_adjudicator_prompt
        return _get_adjudicator_prompt(self.name)

    def boost_rule_score(self, rule_id: str, haystack: str) -> int:
        return 0

    def sport_details(self, detections: Any, perception: dict) -> dict | None:
        if detections is None:
            return None
        from services.extractors import get_extractor
        return get_extractor(self.name).extract(detections, perception).model_dump()

    def tracked_evidence(self, detections: Any) -> dict | None:
        return None

    def metadata_provider(self) -> Any | None:
        return None
