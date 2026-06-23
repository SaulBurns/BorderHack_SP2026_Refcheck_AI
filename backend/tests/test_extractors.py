import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    FrameDetections,
    RawDetections,
)
from services.extractors import (
    BasketballDetailExtractor,
    EmptyDetailExtractor,
    ExtractorRegistry,
    HockeyDetailExtractor,
    LacrosseDetailExtractor,
    SoccerDetailExtractor,
    SportDetailExtractor,
    get_extractor,
    registry,
)
from services.perception_schema import (
    BasketballDetails,
    EmptySportDetails,
    HockeyDetails,
    LacrosseDetails,
    SoccerDetails,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obj(label, x, y, w, h, conf=0.9):
    return DetectionObject(label=label, confidence=conf, bbox=BoundingBox(x=x, y=y, width=w, height=h))

def _detections(*frame_object_lists):
    frames = [
        FrameDetections(frame_index=i, objects=list(objs))
        for i, objs in enumerate(frame_object_lists)
    ]
    return RawDetections(model="test", detector_version="t", frames=frames)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_registry_resolves_each_sport():
    assert isinstance(get_extractor("basketball"), BasketballDetailExtractor)
    assert isinstance(get_extractor("hockey"), HockeyDetailExtractor)
    assert isinstance(get_extractor("soccer"), SoccerDetailExtractor)
    assert isinstance(get_extractor("lacrosse"), LacrosseDetailExtractor)

def test_registry_unknown_sport_falls_back_to_empty():
    assert isinstance(get_extractor("curling"), EmptyDetailExtractor)

def test_registry_none_and_empty_fall_back():
    assert isinstance(get_extractor(None), EmptyDetailExtractor)
    assert isinstance(get_extractor(""), EmptyDetailExtractor)

def test_registry_is_case_insensitive():
    assert isinstance(get_extractor("Basketball"), BasketballDetailExtractor)
    assert isinstance(get_extractor("  HOCKEY "), HockeyDetailExtractor)

def test_registry_available_lists_four_sports():
    assert registry.available() == ["basketball", "hockey", "lacrosse", "soccer"]

def test_custom_registry_register_and_create():
    reg = ExtractorRegistry()
    reg.register("basketball", BasketballDetailExtractor)
    assert isinstance(reg.create("basketball"), BasketballDetailExtractor)
    assert reg.available() == ["basketball"]
    assert isinstance(reg.create("unknown"), EmptyDetailExtractor)

@pytest.mark.parametrize(
    "extractor_cls",
    [BasketballDetailExtractor, HockeyDetailExtractor, SoccerDetailExtractor,
     LacrosseDetailExtractor, EmptyDetailExtractor],
)
def test_extractors_satisfy_protocol(extractor_cls):
    assert isinstance(extractor_cls(), SportDetailExtractor)


# ---------------------------------------------------------------------------
# Basketball — no detections (preserve existing behavior)
# ---------------------------------------------------------------------------

_FULL_PERCEPTION = {
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
}


def test_basketball_no_detections_empty_perception_is_defaults():
    result = BasketballDetailExtractor().extract(None, {})
    assert result == BasketballDetails()

def test_basketball_no_detections_reads_perception_legacy():
    result = BasketballDetailExtractor().extract(None, _FULL_PERCEPTION)
    assert result.offensive_control_status == "airborne_shooter"
    assert result.defender_status.legal_guarding_position == "not_established"
    assert result.court_geometry.key_zone == "restricted_area"


# ---------------------------------------------------------------------------
# Basketball — with detections (derive offensive_control_status)
# ---------------------------------------------------------------------------

def test_basketball_ball_inside_player_is_gathered():
    # ball center (0.5, 0.5) inside a person box centered there.
    dets = _detections([_obj("person", 0.5, 0.5, 0.4, 0.8), _obj("sports ball", 0.5, 0.5, 0.05, 0.05)])
    result = BasketballDetailExtractor().extract(dets, {})
    assert result.offensive_control_status == "gathered"

def test_basketball_ball_away_from_players_is_loose():
    dets = _detections([_obj("person", 0.2, 0.5, 0.1, 0.2), _obj("sports ball", 0.9, 0.9, 0.05, 0.05)])
    result = BasketballDetailExtractor().extract(dets, {})
    assert result.offensive_control_status == "loose_ball"

def test_basketball_no_ball_preserves_perception_value():
    dets = _detections([_obj("person", 0.5, 0.5, 0.4, 0.8)])  # no ball
    result = BasketballDetailExtractor().extract(dets, {"offensive_control_status": "dribbling"})
    assert result.offensive_control_status == "dribbling"  # not overridden

def test_basketball_derivation_overrides_perception():
    dets = _detections([_obj("person", 0.5, 0.5, 0.4, 0.8), _obj("sports ball", 0.5, 0.5, 0.05, 0.05)])
    result = BasketballDetailExtractor().extract(dets, {"offensive_control_status": "dribbling"})
    assert result.offensive_control_status == "gathered"

def test_basketball_detections_preserve_defender_and_geometry():
    # Only offensive_control_status is derived; other blocks come from perception.
    dets = _detections([_obj("person", 0.5, 0.5, 0.4, 0.8), _obj("sports ball", 0.5, 0.5, 0.05, 0.05)])
    result = BasketballDetailExtractor().extract(dets, _FULL_PERCEPTION)
    assert result.offensive_control_status == "gathered"  # derived
    assert result.defender_status.legal_guarding_position == "not_established"  # from perception
    assert result.court_geometry.key_zone == "restricted_area"  # from perception

def test_basketball_controlled_in_any_frame_counts():
    dets = _detections(
        [_obj("person", 0.2, 0.5, 0.1, 0.2), _obj("sports ball", 0.9, 0.9, 0.05, 0.05)],  # loose
        [_obj("person", 0.5, 0.5, 0.4, 0.8), _obj("sports ball", 0.5, 0.5, 0.05, 0.05)],  # controlled
    )
    assert BasketballDetailExtractor().extract(dets, {}).offensive_control_status == "gathered"


# ---------------------------------------------------------------------------
# Backward-compatibility parity with the live _frontend_perception output
# ---------------------------------------------------------------------------

from services.ai_analyzer import _frontend_perception


@pytest.mark.parametrize("perception", [_FULL_PERCEPTION, {}, {"summary": "x"}])
def test_no_detection_extract_matches_frontend_perception(perception):
    out = _frontend_perception(perception, "mock", "", "basketball")
    expected = out["sport_details"]["basketball"]
    actual = BasketballDetailExtractor().extract(None, perception).model_dump()
    assert actual == expected


# ---------------------------------------------------------------------------
# Placeholder extractors
# ---------------------------------------------------------------------------

def test_hockey_extractor_returns_defaults_ignoring_detections():
    dets = _detections([_obj("person", 0.5, 0.5, 0.4, 0.8)])
    assert HockeyDetailExtractor().extract(dets, {}) == HockeyDetails()
    assert HockeyDetailExtractor().extract(None, {}) == HockeyDetails()

def test_soccer_extractor_returns_defaults():
    assert SoccerDetailExtractor().extract(None, {}) == SoccerDetails()

def test_lacrosse_extractor_returns_defaults():
    assert LacrosseDetailExtractor().extract(None, {}) == LacrosseDetails()

def test_empty_extractor_returns_empty_details():
    assert EmptyDetailExtractor().extract(None, {}) == EmptySportDetails()
