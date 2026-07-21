"""Generic sport plugin — the fallback for sports without a full implementation.

As of Sprint 12 every shipped sport (basketball, soccer, hockey, lacrosse) has a
full plugin, so this fallback now serves only *unregistered* sports (an arbitrary
sport string the registry does not know): Claude-only perception via the shared
prompt catalog's stub prompts, no rule boosts, no tracking evidence, and no game
context. The empty-detail extractor still yields a valid (empty) sport-details
block, so the response shape is unchanged.
"""

from __future__ import annotations

from typing import Any

from sports.base import Sport


class GenericSport(Sport):
    """Behavior for a sport that has no dedicated plugin yet."""

    def __init__(self, name: str) -> None:
        self.name = (name or "").lower().strip()
        self.display_name = self.name.replace("_", " ").title() or "Unknown"

    # Prompts call the stub builders directly (NOT `_get_*_prompt`, which now
    # delegates back to this plugin — that would recurse).
    def perception_prompt(self) -> str:
        from services.analysis.prompts import _make_stub_perception_prompt
        return _make_stub_perception_prompt(self.name)

    def adjudicator_prompt(self) -> str:
        from services.analysis.prompts import _make_stub_adjudicator_prompt
        return _make_stub_adjudicator_prompt(self.name)

    def rule_records(self) -> dict:
        return {}

    def detail_extractor(self) -> Any:
        from services.extractors.placeholders import EmptyDetailExtractor
        return EmptyDetailExtractor()

    def details_model(self) -> Any:
        from services.perception_schema import EmptySportDetails
        return EmptySportDetails

    def sport_details(self, detections: Any, perception: dict) -> dict | None:
        if detections is None:
            return None
        return self.detail_extractor().extract(detections, perception).model_dump()

    def tracked_evidence(self, detections: Any) -> dict | None:
        return None

    def metadata_provider(self) -> Any | None:
        return None
