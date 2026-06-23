import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.detectors.detection_models import (
    BoundingBox,
    DetectionObject,
    FrameDetections,
    RawDetections,
)
from services.extractors.basketball_vision import (
    analyze_basketball,
    identify_primary_defender,
    movement_direction,
    possession_status,
    track_players,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obj(label, x, y, w, h, track_id=None):
    return DetectionObject(
        label=label, confidence=0.9, bbox=BoundingBox(x=x, y=y, width=w, height=h), track_id=track_id
    )

def _dets(*frame_object_lists):
    return RawDetections(
        model="t",
        detector_version="t",
        frames=[FrameDetections(frame_index=i, objects=list(objs)) for i, objs in enumerate(frame_object_lists)],
    )

def _bbox(x, y, w=0.2, h=0.4):
    return BoundingBox(x=x, y=y, width=w, height=h)


# ---------------------------------------------------------------------------
# track_players
# ---------------------------------------------------------------------------

def test_track_players_builds_sorted_trajectories():
    dets = _dets(
        [_obj("person", 0.3, 0.5, 0.2, 0.4, track_id=1)],
        [_obj("person", 0.4, 0.5, 0.2, 0.4, track_id=1)],
    )
    tracks = track_players(dets)
    assert set(tracks) == {1}
    assert [f for f, _ in tracks[1]] == [0, 1]

def test_track_players_ignores_untracked():
    dets = _dets([_obj("person", 0.3, 0.5, 0.2, 0.4)])  # track_id None
    assert track_players(dets) == {}


# ---------------------------------------------------------------------------
# possession_status — transitions
# ---------------------------------------------------------------------------

def test_possession_none_without_ball():
    assert possession_status(_dets([_obj("person", 0.5, 0.5, 0.4, 0.8)])) is None

def test_possession_gathered_single_frame_untracked():
    dets = _dets([_obj("person", 0.5, 0.5, 0.4, 0.8), _obj("sports ball", 0.5, 0.5, 0.05, 0.05)])
    assert possession_status(dets) == "gathered"

def test_possession_loose_ball():
    dets = _dets([_obj("person", 0.2, 0.5, 0.1, 0.2), _obj("sports ball", 0.9, 0.9, 0.05, 0.05)])
    assert possession_status(dets) == "loose_ball"

def test_possession_dribbling_same_player_across_frames():
    dets = _dets(
        [_obj("person", 0.5, 0.5, 0.4, 0.8, track_id=1), _obj("sports ball", 0.5, 0.5, 0.05, 0.05)],
        [_obj("person", 0.55, 0.5, 0.4, 0.8, track_id=1), _obj("sports ball", 0.55, 0.5, 0.05, 0.05)],
    )
    assert possession_status(dets) == "dribbling"

def test_possession_passing_between_two_players():
    dets = _dets(
        [_obj("person", 0.3, 0.5, 0.3, 0.8, track_id=1), _obj("sports ball", 0.3, 0.5, 0.05, 0.05)],
        [_obj("person", 0.7, 0.5, 0.3, 0.8, track_id=2), _obj("sports ball", 0.7, 0.5, 0.05, 0.05)],
    )
    assert possession_status(dets) == "passing"


# ---------------------------------------------------------------------------
# movement_direction
# ---------------------------------------------------------------------------

def test_movement_none_with_single_point():
    assert movement_direction([(0, _bbox(0.5, 0.5))]) is None

def test_movement_stationary():
    assert movement_direction([(0, _bbox(0.5, 0.5)), (1, _bbox(0.5, 0.5))]) == "stationary"

def test_movement_lateral():
    assert movement_direction([(0, _bbox(0.3, 0.5)), (1, _bbox(0.7, 0.5))]) == "lateral"

def test_movement_vertical_upward():
    assert movement_direction([(0, _bbox(0.5, 0.6)), (1, _bbox(0.5, 0.4))]) == "vertical"

def test_movement_forward_downward():
    assert movement_direction([(0, _bbox(0.5, 0.4)), (1, _bbox(0.5, 0.7))]) == "forward"


# ---------------------------------------------------------------------------
# identify_primary_defender
# ---------------------------------------------------------------------------

def test_identify_defender_found():
    dets = _dets([
        _obj("person", 0.5, 0.5, 0.3, 0.8),  # handler
        _obj("sports ball", 0.5, 0.5, 0.05, 0.05),
        _obj("person", 0.65, 0.5, 0.3, 0.8, track_id=2),  # defender
    ])
    track_id, found = identify_primary_defender(dets)
    assert found is True
    assert track_id == 2

def test_identify_defender_none_when_only_handler():
    dets = _dets([_obj("person", 0.5, 0.5, 0.3, 0.8), _obj("sports ball", 0.5, 0.5, 0.05, 0.05)])
    assert identify_primary_defender(dets) == (None, False)

def test_identify_defender_none_when_no_control():
    dets = _dets([_obj("person", 0.2, 0.5, 0.2, 0.4), _obj("sports ball", 0.9, 0.9, 0.05, 0.05)])
    assert identify_primary_defender(dets) == (None, False)


# ---------------------------------------------------------------------------
# analyze_basketball (integration of features)
# ---------------------------------------------------------------------------

def test_analyze_basketball_full_features():
    dets = _dets(
        [
            _obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1),  # handler
            _obj("sports ball", 0.5, 0.5, 0.05, 0.05),
            _obj("person", 0.8, 0.5, 0.2, 0.6, track_id=2),  # defender
        ],
        [
            _obj("person", 0.5, 0.5, 0.3, 0.8, track_id=1),
            _obj("sports ball", 0.5, 0.5, 0.05, 0.05),
            _obj("person", 0.9, 0.5, 0.2, 0.6, track_id=2),  # defender moved right -> lateral
        ],
    )
    features = analyze_basketball(dets)
    assert features.offensive_control_status == "dribbling"  # same handler tid across frames
    assert features.primary_or_secondary == "primary"
    assert features.moving_direction == "lateral"

def test_analyze_basketball_insufficient_returns_none_fields():
    features = analyze_basketball(_dets([_obj("person", 0.5, 0.5, 0.3, 0.8)]))  # no ball, no defender
    assert features.offensive_control_status is None
    assert features.primary_or_secondary is None
    assert features.moving_direction is None
