import os
import sys

# Run from backend/ so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pydantic import ValidationError

from services.perception_schema import (
    SCHEMA_VERSION,
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
    out = _frontend_perception(_LEGACY_PERCEPTION_INPUT, "anthropic_four_agent", "blocking foul", "basketball")
    assert set(out.keys()) == _EXPECTED_TOP_LEVEL_KEYS

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
