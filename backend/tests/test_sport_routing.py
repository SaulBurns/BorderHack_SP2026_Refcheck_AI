import sys
import os

# Run from backend/ so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from rules.sport_config import normalize_sport, get_rules_for_sport, SPORTS


# ---------------------------------------------------------------------------
# normalize_sport
# ---------------------------------------------------------------------------

def test_normalize_sport_lowercase():
    assert normalize_sport("basketball") == "basketball"

def test_normalize_sport_titlecase():
    assert normalize_sport("Basketball") == "basketball"

def test_normalize_sport_uppercase():
    assert normalize_sport("HOCKEY") == "hockey"

def test_normalize_sport_strips_whitespace():
    assert normalize_sport("  soccer  ") == "soccer"

def test_normalize_sport_unknown_falls_back_to_basketball():
    assert normalize_sport("curling") == "basketball"

def test_normalize_sport_empty_string_falls_back():
    assert normalize_sport("") == "basketball"

def test_normalize_sport_none_falls_back():
    assert normalize_sport(None) == "basketball"


# ---------------------------------------------------------------------------
# get_rules_for_sport
# ---------------------------------------------------------------------------

def test_get_rules_basketball_returns_nonempty_dict():
    rules = get_rules_for_sport("basketball")
    assert len(rules) > 0

def test_get_rules_basketball_has_block_charge():
    rules = get_rules_for_sport("basketball")
    assert "block_charge" in rules

def test_get_rules_hockey_returns_empty_dict():
    assert get_rules_for_sport("hockey") == {}

def test_get_rules_soccer_returns_empty_dict():
    assert get_rules_for_sport("soccer") == {}

def test_get_rules_lacrosse_returns_empty_dict():
    assert get_rules_for_sport("lacrosse") == {}

def test_get_rules_unknown_sport_returns_empty_dict():
    assert get_rules_for_sport("curling") == {}


# ---------------------------------------------------------------------------
# SPORTS registry shape
# ---------------------------------------------------------------------------

def test_sports_has_exactly_four_entries():
    assert set(SPORTS.keys()) == {"basketball", "hockey", "soccer", "lacrosse"}

def test_sports_entries_have_display_name():
    for key, config in SPORTS.items():
        assert "display_name" in config, f"{key} missing display_name"

def test_sports_entries_have_rules_key():
    for key, config in SPORTS.items():
        assert "rules" in config, f"{key} missing rules key"


# ---------------------------------------------------------------------------
# Prompt selectors
# ---------------------------------------------------------------------------

from services.ai_analyzer import (
    _get_perception_prompt,
    _get_retrieval_prompt,
    _get_adjudicator_prompt,
)


# --- _get_perception_prompt ---

def test_perception_prompt_basketball_contains_basketball_terms():
    prompt = _get_perception_prompt("basketball")
    assert "basketball" in prompt.lower()
    assert "restricted area" in prompt.lower()

def test_perception_prompt_hockey_does_not_mention_restricted_area():
    prompt = _get_perception_prompt("hockey")
    assert "restricted area" not in prompt.lower()

def test_perception_prompt_returns_nonempty_string_for_all_sports():
    for sport in ("basketball", "hockey", "soccer", "lacrosse"):
        result = _get_perception_prompt(sport)
        assert isinstance(result, str) and len(result) > 100, f"empty prompt for {sport}"


# --- _get_retrieval_prompt ---

def test_retrieval_prompt_basketball_mentions_basketball_specific_terms():
    prompt = _get_retrieval_prompt("basketball")
    assert any(
        term in prompt.lower()
        for term in ("pivot foot", "restricted area", "airborne shooter")
    )

def test_retrieval_prompt_hockey_does_not_mention_pivot_foot():
    prompt = _get_retrieval_prompt("hockey")
    assert "pivot foot" not in prompt.lower()

def test_retrieval_prompt_returns_nonempty_string_for_all_sports():
    for sport in ("basketball", "hockey", "soccer", "lacrosse"):
        result = _get_retrieval_prompt(sport)
        assert isinstance(result, str) and len(result) > 50, f"empty prompt for {sport}"


# --- _get_adjudicator_prompt ---

def test_adjudicator_prompt_basketball_mentions_nba():
    prompt = _get_adjudicator_prompt("basketball")
    assert "nba" in prompt.lower()

def test_adjudicator_prompt_hockey_does_not_mention_nba():
    prompt = _get_adjudicator_prompt("hockey")
    assert "nba" not in prompt.lower()

def test_adjudicator_prompt_returns_nonempty_string_for_all_sports():
    for sport in ("basketball", "hockey", "soccer", "lacrosse"):
        result = _get_adjudicator_prompt(sport)
        assert isinstance(result, str) and len(result) > 100, f"empty prompt for {sport}"


# ---------------------------------------------------------------------------
# Rule routing
# ---------------------------------------------------------------------------

from services.ai_analyzer import _rule_records, _retrieve_rules

_MINIMAL_PERCEPTION: dict = {
    "event_type": "unclear",
    "summary": "a play",
    "offensive_control_status": "unclear",
    "defender_status": {},
    "court_geometry": {},
}


def test_rule_records_basketball_returns_nine_rules():
    assert len(_rule_records("basketball")) == 9

def test_rule_records_basketball_has_block_charge():
    ids = [r["rule_id"] for r in _rule_records("basketball")]
    assert "BLOCK_CHARGE" in ids

def test_rule_records_hockey_returns_empty_list():
    assert _rule_records("hockey") == ()

def test_rule_records_soccer_returns_empty_list():
    assert _rule_records("soccer") == ()

def test_rule_records_lacrosse_returns_empty_list():
    assert _rule_records("lacrosse") == ()


def test_retrieve_rules_basketball_returns_block_charge_first_for_blocking_query():
    perception = {
        **_MINIMAL_PERCEPTION,
        "event_type": "possible_blocking_foul",
        "summary": "defender slides into path of ball handler",
        "defender_status": {
            "primary_or_secondary": "primary",
            "legal_guarding_position": "not_established",
            "moving_direction": "lateral",
            "inside_restricted_area": False,
        },
        "court_geometry": {"key_zone": "paint_lane"},
    }
    rules = _retrieve_rules("blocking foul legal guarding position established", perception, "basketball")
    assert 1 <= len(rules) <= 5
    assert rules[0]["rule_id"] == "BLOCK_CHARGE"

def test_retrieve_rules_hockey_returns_empty_list():
    rules = _retrieve_rules("hockey slashing high stick", _MINIMAL_PERCEPTION, "hockey")
    assert rules == []

def test_retrieve_rules_basketball_preserves_existing_behavior():
    perception = {
        **_MINIMAL_PERCEPTION,
        "event_type": "possible_blocking_foul",
        "defender_status": {"moving_direction": "lateral", "inside_restricted_area": False},
        "court_geometry": {"key_zone": "restricted_area"},
    }
    rules = _retrieve_rules("blocking charge restricted area secondary defender", perception, "basketball")
    assert len(rules) > 0
    assert rules[0]["rule_id"] in ("BLOCK_CHARGE", "RESTRICTED_AREA")


# ---------------------------------------------------------------------------
# Output sport field correctness
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock
from services.ai_analyzer import _mock_ai_result, _frontend_perception, _rule_by_id


def test_mock_ai_result_sport_field_matches_hockey():
    mock_file = MagicMock()
    result = _mock_ai_result(mock_file, "hockey", "", "", "", "", None, "test fallback")
    assert result["perception"]["sport"] == "hockey"

def test_mock_ai_result_sport_field_matches_basketball():
    mock_file = MagicMock()
    result = _mock_ai_result(mock_file, "basketball", "", "", "", "", None, "test fallback")
    assert result["perception"]["sport"] == "basketball"

def test_mock_ai_result_sport_field_matches_soccer():
    mock_file = MagicMock()
    result = _mock_ai_result(mock_file, "soccer", "", "", "", "", None, "test fallback")
    assert result["perception"]["sport"] == "soccer"


def test_frontend_perception_sport_field_hockey():
    result = _frontend_perception({"event_type": "unclear", "summary": "test"}, "mock", "", "hockey")
    assert result["sport"] == "hockey"

def test_frontend_perception_sport_field_basketball():
    result = _frontend_perception({"event_type": "unclear", "summary": "test"}, "mock", "", "basketball")
    assert result["sport"] == "basketball"


def test_rule_by_id_with_empty_rules_returns_no_rule_placeholder():
    result = _rule_by_id(None, [])
    assert result["rule_id"] == "NO_RULE"

def test_rule_by_id_finds_exact_match():
    rules = [
        {"rule_id": "BLOCK_CHARGE", "section_title": "test", "text": "test", "page_number": 1, "call_type": "Block"},
    ]
    assert _rule_by_id("BLOCK_CHARGE", rules)["rule_id"] == "BLOCK_CHARGE"

def test_rule_by_id_returns_first_rule_when_id_not_found():
    rules = [
        {"rule_id": "BLOCK_CHARGE", "section_title": "test", "text": "test", "page_number": 1, "call_type": "Block"},
    ]
    assert _rule_by_id("NONEXISTENT", rules)["rule_id"] == "BLOCK_CHARGE"
