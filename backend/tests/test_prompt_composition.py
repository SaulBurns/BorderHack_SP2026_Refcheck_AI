"""Sprint 16C — layered prompt composition (Common → Sport → Task).

Verifies the dedup refactor: every sport composes its prompt from the shared
Common fragments, so the common sections are byte-identical across sports and each
prompt is deterministic — while the sport-specific bodies and required behavior
(verdict fields, valid verdicts, impact-zone note) are preserved.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from rules.sport_config import supported_sports
from services.analysis.prompts import (
    ADJUDICATOR_OUTPUT_INSTRUCTION,
    CITATION_DISCIPLINE,
    PERCEPTION_OUTPUT_HEADER,
    PERCEPTION_VISUAL_QUALITY,
    VALID_VERDICTS,
    compose,
)
from sports import get_sport

_SPORTS = sorted(supported_sports())  # basketball, hockey, lacrosse, soccer


def _perc(sport: str) -> str:
    return get_sport(sport).perception_prompt()


def _adj(sport: str) -> str:
    return get_sport(sport).adjudicator_prompt()


# ---------------------------------------------------------------------------
# compose() helper
# ---------------------------------------------------------------------------

def test_compose_strips_joins_and_drops_empties():
    assert compose("  a  ", "", "   ", "  b ") == "a\n\nb"
    assert compose("only") == "only"
    assert compose() == ""


# ---------------------------------------------------------------------------
# Determinism — "every sport still produces identical prompt content"
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sport", _SPORTS)
def test_prompts_are_deterministic(sport):
    assert _perc(sport) == _perc(sport)
    assert _adj(sport) == _adj(sport)


# ---------------------------------------------------------------------------
# Shared Common fragments are byte-identical across every sport (dedup proof)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fragment", [PERCEPTION_VISUAL_QUALITY, PERCEPTION_OUTPUT_HEADER])
def test_common_perception_fragment_in_every_sport(fragment):
    for sport in _SPORTS:
        assert fragment in _perc(sport), f"{sport} perception missing shared fragment"


@pytest.mark.parametrize("fragment", [VALID_VERDICTS, CITATION_DISCIPLINE, ADJUDICATOR_OUTPUT_INSTRUCTION])
def test_common_adjudicator_fragment_in_every_sport(fragment):
    for sport in _SPORTS:
        assert fragment in _adj(sport), f"{sport} adjudicator missing shared fragment"


def test_shared_opener_is_identical_across_sports():
    # The sport-neutral second sentence of the perception intro must match verbatim.
    common = (
        "Your job is to describe what you observe in structured form. You are NOT issuing a "
        "verdict. A separate agent will rule on the call. Your role is to be the most accurate "
        "possible eyes for the system."
    )
    for sport in _SPORTS:
        assert common in _perc(sport)


# ---------------------------------------------------------------------------
# Behavior preserved
# ---------------------------------------------------------------------------

def test_adjudicator_names_all_verdict_fields_and_values():
    fields = ["verdict", "confidence", "primary_rule_id", "supporting_rule_ids", "reasoning", "flags"]
    values = ["fair_call", "bad_call", "inconclusive"]
    for sport in _SPORTS:
        prompt = _adj(sport)
        for field in fields:
            assert field in prompt, f"{sport} adjudicator dropped field {field}"
        for value in values:
            assert value in prompt, f"{sport} adjudicator dropped verdict {value}"


def test_perception_structure_preserved():
    for sport in _SPORTS:
        prompt = _perc(sport)
        assert "You are NOT issuing a verdict" in prompt
        assert '"event_type"' in prompt
        assert '"summary"' in prompt
        assert "Impact zone should be normalized" in prompt


# ---------------------------------------------------------------------------
# Sport-specific content still present (Sport layer intact)
# ---------------------------------------------------------------------------

def test_sport_specific_content_preserved():
    assert "restricted area" in _perc("basketball") and "NBA" in _adj("basketball")
    assert "blue line" in _perc("hockey").lower() and "NHL" in _adj("hockey")
    assert "penalty area" in _perc("soccer") and "Laws of the Game" in _adj("soccer")
    assert "crease" in _perc("lacrosse") and "NCAA" in _adj("lacrosse")


def test_hockey_perception_has_no_basketball_geometry():
    # Regression guard: the shared fragments must not leak basketball-only terms.
    assert "restricted area" not in _perc("hockey")
