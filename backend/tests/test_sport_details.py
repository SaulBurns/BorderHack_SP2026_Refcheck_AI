import os
import sys

# Run from backend/ so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from rules.sport_config import SPORTS
from services.perception_schema import (
    SPORT_DETAIL_MODELS,
    BasketballDetails,
    CourtGeometry,
    DefenderStatus,
    EmptySportDetails,
    HockeyDetails,
    LacrosseDetails,
    SoccerDetails,
    SportDetails,
    get_sport_details_model,
)


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------

def test_registry_has_exactly_four_sports():
    assert set(SPORT_DETAIL_MODELS.keys()) == {"basketball", "hockey", "soccer", "lacrosse"}

def test_registry_keys_match_sport_config():
    assert set(SPORT_DETAIL_MODELS.keys()) == set(SPORTS.keys())

def test_all_registered_models_subclass_sport_details():
    for model in SPORT_DETAIL_MODELS.values():
        assert issubclass(model, SportDetails)


# ---------------------------------------------------------------------------
# get_sport_details_model
# ---------------------------------------------------------------------------

def test_get_model_basketball():
    assert get_sport_details_model("basketball") is BasketballDetails

def test_get_model_hockey():
    assert get_sport_details_model("hockey") is HockeyDetails

def test_get_model_soccer():
    assert get_sport_details_model("soccer") is SoccerDetails

def test_get_model_lacrosse():
    assert get_sport_details_model("lacrosse") is LacrosseDetails

def test_get_model_unknown_falls_back_to_empty():
    assert get_sport_details_model("curling") is EmptySportDetails

def test_get_model_is_case_insensitive():
    assert get_sport_details_model("Basketball") is BasketballDetails
    assert get_sport_details_model("  HOCKEY  ") is HockeyDetails

def test_get_model_empty_string_falls_back():
    assert get_sport_details_model("") is EmptySportDetails

def test_get_model_none_falls_back():
    assert get_sport_details_model(None) is EmptySportDetails

def test_get_model_never_raises_for_arbitrary_input():
    # Fallback contract: routing must never crash on an unconfigured sport.
    assert get_sport_details_model("tennis") is EmptySportDetails


# ---------------------------------------------------------------------------
# BasketballDetails — lossless preservation of current fields
# ---------------------------------------------------------------------------

def test_basketball_details_default_field_names_match_legacy():
    details = BasketballDetails()
    assert set(details.model_dump().keys()) == {
        "offensive_control_status",
        "defender_status",
        "court_geometry",
    }

def test_basketball_defender_status_keys_match_legacy():
    assert set(DefenderStatus().model_dump().keys()) == {
        "primary_or_secondary",
        "legal_guarding_position",
        "feet_set_before_contact",
        "moving_direction",
        "inside_restricted_area",
    }

def test_basketball_court_geometry_keys_match_legacy():
    assert set(CourtGeometry().model_dump().keys()) == {
        "key_zone",
        "restricted_area_arc_visible",
        "defender_feet_visible",
        "basket_visible",
    }

def test_basketball_details_defaults_match_legacy_unclear_state():
    details = BasketballDetails()
    assert details.offensive_control_status == "unclear"
    assert details.defender_status.legal_guarding_position == "unclear"
    assert details.defender_status.inside_restricted_area is False
    assert details.court_geometry.key_zone == "backcourt_or_unclear"
    assert details.court_geometry.basket_visible is False

def test_basketball_details_accepts_populated_values():
    details = BasketballDetails(
        offensive_control_status="airborne_shooter",
        defender_status=DefenderStatus(legal_guarding_position="established", inside_restricted_area=True),
        court_geometry=CourtGeometry(key_zone="restricted_area", basket_visible=True),
    )
    assert details.offensive_control_status == "airborne_shooter"
    assert details.defender_status.inside_restricted_area is True
    assert details.court_geometry.key_zone == "restricted_area"

def test_basketball_details_roundtrip():
    details = BasketballDetails(offensive_control_status="dribbling")
    assert BasketballDetails.model_validate(details.model_dump()) == details


# ---------------------------------------------------------------------------
# Placeholder sports — instantiate with neutral defaults
# ---------------------------------------------------------------------------

def test_empty_sport_details_has_no_fields():
    assert EmptySportDetails().model_dump() == {}

def test_hockey_details_defaults():
    h = HockeyDetails()
    assert h.zone == "unclear"
    assert h.goalie_involved is False
    assert h.boards_involved is False

def test_soccer_details_defaults():
    s = SoccerDetails()
    assert s.field_third == "unclear"
    assert s.in_penalty_area is False
    assert s.offside_relevant is False

def test_lacrosse_details_defaults():
    l = LacrosseDetails()
    assert l.crease_violation is False
    assert l.ball_carrier_status == "unclear"

@pytest.mark.parametrize("model", [HockeyDetails, SoccerDetails, LacrosseDetails, EmptySportDetails])
def test_placeholder_models_roundtrip(model):
    instance = model()
    assert model.model_validate(instance.model_dump()) == instance
