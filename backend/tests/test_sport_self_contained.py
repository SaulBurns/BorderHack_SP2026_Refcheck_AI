"""Proof test for the self-contained sport architecture (refactor).

The target architecture: adding a new sport requires ONLY (1) a sports/<sport>/
package implementing the Sport interface and (2) one SportRegistry registration.
No other backend file may need editing.

This test proves that by defining a brand-new sport ("underwater_hockey") entirely
inline — its corpus, prompts, detail model, and extractor all live on the plugin
object, nothing is added to rules/sport_config.py, services/analysis/prompts.py,
services/extractors/registry.py, or services/perception_schema.py — and then
asserting that every generic lookup resolves through the plugin.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.perception_schema import SportDetails
from sports.base import Sport
from sports.registry import registry


# --- A fully self-contained sport, defined here and nowhere else --------------

class _UWHDetails(SportDetails):
    surfaced: bool = False


class _UWHExtractor:
    sport = "underwater_hockey"

    def extract(self, detections, perception):
        return _UWHDetails(surfaced=bool(perception.get("surfaced", False)))


class UnderwaterHockeySport(Sport):
    name = "underwater_hockey"
    display_name = "Underwater Hockey"

    def perception_prompt(self) -> str:
        return "UWH PERCEPTION PROMPT describing the puck on the pool floor."

    def retrieval_prompt(self) -> str:
        return "UWH RETRIEVAL PROMPT"

    def adjudicator_prompt(self) -> str:
        return "UWH ADJUDICATOR PROMPT"

    def boost_rule_score(self, rule_id: str, haystack: str) -> int:
        return 5 if rule_id == "PUCK_ADVANCE" and "puck" in haystack else 0

    def rule_records(self) -> dict:
        return {
            "puck_advance": {
                "call_type": "Puck Advance",
                "rule_applied": "UWH Rule 1 — advancing the puck",
                "summary": "Players may not carry the puck; it must be pushed with the stick.",
            },
        }

    def detail_extractor(self):
        return _UWHExtractor()

    def details_model(self):
        return _UWHDetails

    def sport_details(self, detections, perception: dict):
        if detections is None:
            return None
        return self.detail_extractor().extract(detections, perception).model_dump()

    def tracked_evidence(self, detections):
        return None

    def metadata_provider(self):
        return None


@pytest.fixture
def registered_uwh():
    sport = UnderwaterHockeySport()
    registry.register(sport)
    try:
        yield sport
    finally:
        registry._sports.pop("underwater_hockey", None)


# --- Every generic lookup must resolve through the plugin ---------------------

def test_registry_resolves_new_sport(registered_uwh):
    from sports import get_sport
    assert isinstance(get_sport("underwater_hockey"), UnderwaterHockeySport)

def test_rules_route_through_plugin(registered_uwh):
    from rules.sport_config import get_rules_for_sport
    rules = get_rules_for_sport("underwater_hockey")
    assert set(rules.keys()) == {"puck_advance"}

def test_rule_records_route_through_plugin(registered_uwh):
    from services.ai_analyzer import _rule_records
    ids = [r["rule_id"] for r in _rule_records("underwater_hockey")]
    assert ids == ["PUCK_ADVANCE"]

def test_retrieval_boost_routes_through_plugin(registered_uwh):
    from services.ai_analyzer import _retrieve_rules
    rules = _retrieve_rules("puck advance push stick", {"summary": "puck pushed"}, "underwater_hockey")
    assert rules and rules[0]["rule_id"] == "PUCK_ADVANCE"

def test_perception_prompt_routes_through_plugin(registered_uwh):
    from services.analysis.prompts import _get_perception_prompt
    assert "UWH PERCEPTION PROMPT" in _get_perception_prompt("underwater_hockey")

def test_retrieval_and_adjudicator_prompts_route_through_plugin(registered_uwh):
    from services.analysis.prompts import _get_retrieval_prompt, _get_adjudicator_prompt
    assert _get_retrieval_prompt("underwater_hockey") == "UWH RETRIEVAL PROMPT"
    assert _get_adjudicator_prompt("underwater_hockey") == "UWH ADJUDICATOR PROMPT"

def test_extractor_routes_through_plugin(registered_uwh):
    from services.extractors import get_extractor
    ext = get_extractor("underwater_hockey")
    assert isinstance(ext, _UWHExtractor)
    assert ext.extract(None, {"surfaced": True}).model_dump() == {"surfaced": True}

def test_details_model_routes_through_plugin(registered_uwh):
    from services.perception_schema import get_sport_details_model
    assert get_sport_details_model("underwater_hockey") is _UWHDetails

def test_normalize_recognizes_registered_sport(registered_uwh):
    from rules.sport_config import normalize_sport
    assert normalize_sport("Underwater_Hockey") == "underwater_hockey"

def test_unknown_sport_still_falls_back_everywhere():
    # A sport that is NOT registered still degrades gracefully (no plugin).
    from rules.sport_config import get_rules_for_sport, normalize_sport
    from services.perception_schema import get_sport_details_model, EmptySportDetails
    from services.extractors import get_extractor, EmptyDetailExtractor
    assert get_rules_for_sport("kabaddi") == {}
    assert normalize_sport("kabaddi") == "basketball"
    assert get_sport_details_model("kabaddi") is EmptySportDetails
    assert isinstance(get_extractor("kabaddi"), EmptyDetailExtractor)
