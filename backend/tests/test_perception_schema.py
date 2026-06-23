import os
import sys

# Run from backend/ so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pydantic import ValidationError

from services.perception_schema import (
    SCHEMA_VERSION,
    BasketballDetails,
    Contact,
    FrameObservation,
    ImpactZone,
    ObjectOfPlay,
    PerceptionCore,
    Player,
)


# ---------------------------------------------------------------------------
# PerceptionCore — construction & defaults
# ---------------------------------------------------------------------------

def test_perception_core_requires_sport():
    with pytest.raises(ValidationError):
        PerceptionCore()

def test_perception_core_minimal_construction():
    core = PerceptionCore(sport="basketball")
    assert core.sport == "basketball"
    assert core.schema_version == SCHEMA_VERSION
    assert core.event_type == "unclear"
    assert core.visual_quality == "partial"
    assert core.perception_confidence == 0.5

def test_perception_core_nested_defaults_are_typed():
    core = PerceptionCore(sport="hockey")
    assert isinstance(core.contact, Contact)
    assert isinstance(core.object_of_play, ObjectOfPlay)
    assert isinstance(core.impact_zone, ImpactZone)
    assert core.players_involved == []
    assert core.frame_observations == []
    assert core.moment_of_interest_seconds is None

def test_perception_core_default_collections_are_independent():
    a = PerceptionCore(sport="soccer")
    b = PerceptionCore(sport="soccer")
    a.players_involved.append(Player())
    assert b.players_involved == []


# ---------------------------------------------------------------------------
# PerceptionCore — validation
# ---------------------------------------------------------------------------

def test_perception_confidence_upper_bound_enforced():
    with pytest.raises(ValidationError):
        PerceptionCore(sport="basketball", perception_confidence=1.5)

def test_perception_confidence_lower_bound_enforced():
    with pytest.raises(ValidationError):
        PerceptionCore(sport="basketball", perception_confidence=-0.1)

def test_visual_quality_literal_rejects_unknown_value():
    with pytest.raises(ValidationError):
        PerceptionCore(sport="basketball", visual_quality="grainy")

def test_visual_quality_accepts_all_valid_values():
    for value in ("clear", "partial", "obstructed", "poor"):
        assert PerceptionCore(sport="basketball", visual_quality=value).visual_quality == value


# ---------------------------------------------------------------------------
# Component models — validation
# ---------------------------------------------------------------------------

def test_player_role_literal_rejects_unknown():
    with pytest.raises(ValidationError):
        Player(role="goalie")

def test_player_defaults():
    p = Player()
    assert p.role == "unclear"
    assert p.team_color is None
    assert p.zone is None

def test_contact_severity_literal_rejects_unknown():
    with pytest.raises(ValidationError):
        Contact(severity="catastrophic")

def test_object_of_play_kind_literal():
    assert ObjectOfPlay(kind="puck").kind == "puck"
    with pytest.raises(ValidationError):
        ObjectOfPlay(kind="frisbee")

def test_impact_zone_defaults_center():
    z = ImpactZone()
    assert z.x_percent == 50.0
    assert z.y_percent == 50.0
    assert z.radius_percent == 14.0


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------

def test_perception_core_roundtrip_is_stable():
    core = PerceptionCore(
        sport="basketball",
        event_type="possible_blocking_foul",
        summary="a play",
        players_involved=[Player(role="offense", team_color="red")],
        contact=Contact(detected=True, location="torso", severity="significant"),
        object_of_play=ObjectOfPlay(kind="ball", visible=True, state="dribbling"),
        frame_observations=[FrameObservation(frame_index=1, observation="drive")],
        moment_of_interest_seconds=4.2,
        perception_confidence=0.77,
    )
    dumped = core.model_dump()
    assert PerceptionCore.model_validate(dumped) == core


# ---------------------------------------------------------------------------
# Golden / characterization test — current basketball perception output shape.
#
# Locks the EXACT shape produced by the live _frontend_perception() today, so
# the Phase 2 rewire cannot silently drop or rename a field. This intentionally
# asserts the LEGACY (basketball-shaped) keys, not the new schema.
# ---------------------------------------------------------------------------

from services.ai_analyzer import _frontend_perception

_LEGACY_PERCEPTION_INPUT = {
    "event_type": "possible_blocking_foul",
    "summary": "Defender slides into the path of the ball handler near the lane.",
    "players_involved": [
        {
            "role": "offense",
            "jersey_color": "white",
            "position_description": "driving to the basket",
            "court_zone": "paint_lane",
            "body_state": "airborne",
        }
    ],
    "contact_detected": True,
    "contact_location": "torso",
    "ball_visible": True,
    "ball_state": "gathered",
    "offensive_control_status": "airborne_shooter",
    "defender_status": {
        "primary_or_secondary": "secondary",
        "legal_guarding_position": "not_established",
        "feet_set_before_contact": False,
        "moving_direction": "lateral",
        "inside_restricted_area": True,
    },
    "court_geometry": {
        "key_zone": "restricted_area",
        "restricted_area_arc_visible": True,
        "defender_feet_visible": True,
        "basket_visible": True,
    },
    "frame_observations": [
        {"frame_index": 1, "approx_time_seconds": 0.0, "observation": "drive begins"}
    ],
    "moment_of_interest_seconds": 4.2,
    "impact_zone": {"x_percent": 48, "y_percent": 55, "radius_percent": 12, "label": "contact"},
    "visual_quality": "clear",
    "perception_confidence": 0.82,
    "notes": "clear angle",
}

_EXPECTED_TOP_LEVEL_KEYS = {
    "sport",
    "event_type",
    "summary",
    "players_involved",
    "contact_detected",
    "contact_location",
    "ball_visible",
    "ball_state",
    "offensive_control_status",
    "defender_status",
    "court_geometry",
    "frame_observations",
    "moment_of_interest_seconds",
    "impact_zone",
    "visual_quality",
    "perception_confidence",
    "notes",
}


def test_golden_frontend_perception_top_level_keys_unchanged():
    # Phase 2 is additive: every legacy key must still be present (no removals).
    # New keys (schema_version, sport_details) are allowed on top — asserted as a
    # subset rather than exact equality.
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "anthropic_four_agent", "blocking foul", "basketball")
    assert _EXPECTED_TOP_LEVEL_KEYS <= set(out.keys())

def test_golden_frontend_perception_defender_status_keys_unchanged():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "mock", "", "basketball")
    assert set(out["defender_status"].keys()) == {
        "primary_or_secondary",
        "legal_guarding_position",
        "feet_set_before_contact",
        "moving_direction",
        "inside_restricted_area",
    }

def test_golden_frontend_perception_court_geometry_keys_unchanged():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "mock", "", "basketball")
    assert set(out["court_geometry"].keys()) == {
        "key_zone",
        "restricted_area_arc_visible",
        "defender_feet_visible",
        "basket_visible",
    }

def test_golden_frontend_perception_passes_values_through():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "anthropic_four_agent", "q", "basketball")
    assert out["sport"] == "basketball"
    assert out["event_type"] == "possible_blocking_foul"
    assert out["court_geometry"]["key_zone"] == "restricted_area"
    assert out["defender_status"]["legal_guarding_position"] == "not_established"
    assert out["perception_confidence"] == 0.82

def test_golden_frontend_perception_sport_field_follows_argument():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "mock", "", "hockey")
    assert out["sport"] == "hockey"


# ---------------------------------------------------------------------------
# Phase 2 — backward-compatible sport_details migration.
#
# The response must carry BOTH the legacy top-level basketball fields AND the
# new schema_version + sport_details block, with synchronized values.
# ---------------------------------------------------------------------------

def test_phase2_schema_version_emitted():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "anthropic_four_agent", "q", "basketball")
    assert out["schema_version"] == SCHEMA_VERSION
    assert isinstance(out["schema_version"], int)

def test_phase2_legacy_basketball_fields_still_present():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "mock", "", "basketball")
    for key in ("offensive_control_status", "defender_status", "court_geometry"):
        assert key in out, f"legacy field {key} was removed"

def test_phase2_sport_details_present_and_keyed_by_sport():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "mock", "", "basketball")
    assert "sport_details" in out
    assert "basketball" in out["sport_details"]

def test_phase2_sport_details_basketball_has_expected_keys():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "mock", "", "basketball")
    assert set(out["sport_details"]["basketball"].keys()) == {
        "offensive_control_status",
        "defender_status",
        "court_geometry",
    }

def test_phase2_legacy_and_new_values_synchronized():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "anthropic_four_agent", "q", "basketball")
    details = out["sport_details"]["basketball"]
    assert details["offensive_control_status"] == out["offensive_control_status"]
    assert details["defender_status"] == out["defender_status"]
    assert details["court_geometry"] == out["court_geometry"]

def test_phase2_sport_details_basketball_validates_against_model():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "mock", "", "basketball")
    # Round-trips cleanly through the Pydantic model — i.e. it's a valid response.
    model = BasketballDetails.model_validate(out["sport_details"]["basketball"])
    assert model.model_dump() == out["sport_details"]["basketball"]

def test_phase2_defaults_path_stays_synchronized():
    # When perception omits the basketball blocks, legacy defaults and the new
    # block must still match (both derived from the same computed values).
    out = _frontend_perception({"event_type": "unclear", "summary": "x"}, "mock", "", "basketball")
    details = out["sport_details"]["basketball"]
    assert details["defender_status"] == out["defender_status"]
    assert details["court_geometry"] == out["court_geometry"]
    assert details["offensive_control_status"] == out["offensive_control_status"]

def test_phase2_non_basketball_sport_details_uses_placeholder():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "mock", "", "hockey")
    # Legacy basketball fields are still present (unchanged behavior)...
    assert "defender_status" in out and "court_geometry" in out
    # ...and sport_details carries the hockey placeholder, not basketball.
    assert "hockey" in out["sport_details"]
    assert "offensive_control_status" not in out["sport_details"]["hockey"]

def test_phase2_unknown_sport_details_is_empty_block():
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "mock", "", "curling")
    assert out["sport_details"] == {"curling": {}}
