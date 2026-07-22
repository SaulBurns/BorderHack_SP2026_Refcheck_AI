"""Hockey sport plugin tests (Sprint 11 — second new sport).

Covers the full hockey plugin surface: registry resolution, prompts, rule
corpus, the detail extractor, and the tracking-evidence layer, plus
the pipeline seams (sport_details / tracked_evidence delegation) that make
``sport="hockey"`` route through the plugin without any core-pipeline change.
"""

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obj(label, x, y, w=0.1, h=0.2, track_id=None):
    return DetectionObject(
        label=label, confidence=0.9, bbox=BoundingBox(x=x, y=y, width=w, height=h), track_id=track_id
    )

def _dets(*frame_object_lists):
    return RawDetections(
        model="t",
        detector_version="t",
        frames=[FrameDetections(frame_index=i, objects=list(objs)) for i, objs in enumerate(frame_object_lists)],
    )


# ---------------------------------------------------------------------------
# Registry resolution
# ---------------------------------------------------------------------------

def test_registry_lists_hockey():
    from sports.registry import registry
    assert "hockey" in registry.available()

def test_get_sport_hockey_returns_hockey_plugin():
    from sports import get_sport
    from sports.hockey import HockeySport
    sport = get_sport("hockey")
    assert isinstance(sport, HockeySport)
    assert sport.name == "hockey"

def test_get_sport_hockey_is_case_insensitive():
    from sports import get_sport
    from sports.hockey import HockeySport
    assert isinstance(get_sport("  Hockey  "), HockeySport)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def test_hockey_perception_prompt_mentions_hockey_terms():
    from sports.hockey.prompts import perception_prompt
    prompt = perception_prompt().lower()
    assert "blue line" in prompt
    assert "icing" in prompt
    assert "boarding" in prompt

def test_hockey_perception_prompt_avoids_basketball_geometry():
    from sports.hockey.prompts import perception_prompt
    assert "restricted area" not in perception_prompt().lower()

def test_hockey_adjudicator_prompt_mentions_nhl_not_nba():
    from sports.hockey.prompts import adjudicator_prompt
    prompt = adjudicator_prompt().lower()
    assert "nhl" in prompt
    assert "nba" not in prompt

def test_catalog_resolves_real_hockey_prompt_not_stub():
    from services.analysis.prompts import _get_perception_prompt
    prompt = _get_perception_prompt("hockey").lower()
    assert "blue line" in prompt
    assert "not yet configured" not in prompt

def test_plugin_prompt_matches_catalog():
    from sports import get_sport
    from services.analysis.prompts import _get_perception_prompt
    assert get_sport("hockey").perception_prompt() == _get_perception_prompt("hockey")


# ---------------------------------------------------------------------------
# Rule corpus
# ---------------------------------------------------------------------------

def test_hockey_rules_cover_supported_events():
    from rules.hockey_rules import HOCKEY_RULES
    assert set(HOCKEY_RULES.keys()) == {
        "icing", "offside", "tripping", "cross_checking", "boarding", "slashing", "hooking",
    }

def test_hockey_rule_records_have_expected_shape():
    from services.ai_analyzer import _rule_records
    records = _rule_records("hockey")
    assert len(records) == 7
    for r in records:
        assert set(r.keys()) >= {"rule_id", "section_title", "text", "call_type"}
        assert r["rule_id"] == r["rule_id"].upper()

# ---------------------------------------------------------------------------
# Detail extractor
# ---------------------------------------------------------------------------

def test_hockey_extractor_registered():
    from services.extractors import get_extractor
    from sports.hockey.extractor import HockeyDetailExtractor
    assert isinstance(get_extractor("hockey"), HockeyDetailExtractor)

def test_hockey_extractor_defaults_from_empty_perception():
    from sports.hockey.extractor import HockeyDetailExtractor
    details = HockeyDetailExtractor().extract(None, {})
    assert details.zone == "unclear"
    assert details.goalie_involved is False
    assert details.boards_involved is False

def test_hockey_extractor_reads_perception_fields():
    from sports.hockey.extractor import HockeyDetailExtractor
    details = HockeyDetailExtractor().extract(
        None,
        {
            "zone": "along_boards",
            "goalie_involved": True,
            "puck_possession": "attacker",
            "infraction_candidate": "boarding",
            "boards_involved": True,
        },
    )
    dumped = details.model_dump()
    assert dumped["zone"] == "along_boards"
    assert dumped["goalie_involved"] is True
    assert dumped["infraction_candidate"] == "boarding"
    assert dumped["boards_involved"] is True

def test_hockey_extractor_roundtrips_through_shared_registry():
    from services.extractors import get_extractor
    details = get_extractor("hockey").extract(None, {"boards_involved": True})
    assert details.model_dump()["boards_involved"] is True


# ---------------------------------------------------------------------------
# Tracking evidence
# ---------------------------------------------------------------------------

def test_tracked_evidence_none_without_detections():
    from sports.hockey.tracking import summarize_tracked_evidence
    assert summarize_tracked_evidence(None) is None

def test_tracked_evidence_none_for_empty_frames():
    from sports.hockey.tracking import summarize_tracked_evidence
    assert summarize_tracked_evidence(_dets([], [])) is None

def test_tracked_evidence_derives_possession_and_rush():
    from sports.hockey.tracking import summarize_tracked_evidence
    # Player 1 carries the puck moving left-to-right across two frames.
    dets = _dets(
        [_obj("person", 0.30, 0.5, track_id=1), _obj("person", 0.60, 0.5, track_id=2), _obj("puck", 0.30, 0.5)],
        [_obj("person", 0.55, 0.5, track_id=1), _obj("person", 0.80, 0.5, track_id=2), _obj("puck", 0.55, 0.5)],
    )
    ev = summarize_tracked_evidence(dets)
    assert ev is not None
    assert ev["players_tracked"] == 2
    assert ev["frames_with_puck"] == 2
    assert ev["possession_summary"] == "in_possession"
    assert ev["rush_direction"] == "left_to_right"
    assert 0.0 <= ev["tracking_confidence"] <= 1.0

def test_tracked_evidence_recognizes_sports_ball_label_as_puck():
    from sports.hockey.tracking import summarize_tracked_evidence
    dets = _dets([_obj("person", 0.5, 0.5, track_id=1), _obj("sports ball", 0.5, 0.5)])
    ev = summarize_tracked_evidence(dets)
    assert ev["frames_with_puck"] == 1


# ---------------------------------------------------------------------------
# Pipeline seams — the plugin owns sport-specific behavior
# ---------------------------------------------------------------------------

def test_plugin_sport_details_none_without_detections():
    from sports import get_sport
    assert get_sport("hockey").sport_details(None, {}) is None

def test_plugin_sport_details_with_detections():
    from sports import get_sport
    dets = _dets([_obj("person", 0.5, 0.5, track_id=1), _obj("puck", 0.5, 0.5)])
    details = get_sport("hockey").sport_details(dets, {"boards_involved": True})
    assert details["boards_involved"] is True

def test_plugin_tracked_evidence_delegates_to_tracking():
    from sports import get_sport
    dets = _dets([_obj("person", 0.5, 0.5, track_id=1), _obj("puck", 0.5, 0.5)])
    ev = get_sport("hockey").tracked_evidence(dets)
    assert ev is not None and "tracking_confidence" in ev

def test_plugin_metadata_provider_is_none():
    from sports import get_sport
    assert get_sport("hockey").metadata_provider() is None

def test_mock_result_sport_field_hockey():
    from unittest.mock import MagicMock
    from services.ai_analyzer import _mock_ai_result
    result = _mock_ai_result(MagicMock(), "hockey", "", "", "", "", None, "test fallback")
    assert result["perception"]["sport"] == "hockey"

def test_frontend_perception_hockey_has_sport_details_block():
    from services.ai_analyzer import _frontend_perception
    result = _frontend_perception({"event_type": "possible_boarding", "summary": "test"}, "mock", "hockey")
    assert result["sport"] == "hockey"
    assert "hockey" in result["sport_details"]
