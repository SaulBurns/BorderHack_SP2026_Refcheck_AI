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
