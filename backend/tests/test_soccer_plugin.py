"""Soccer sport plugin tests (Sprint 10 — first new sport).

Covers the full soccer plugin surface: registry resolution, prompts, the rule
corpus, the detail extractor, and the tracking-evidence layer, plus
the pipeline seams (sport_details / tracked_evidence delegation) that make
``sport="soccer"`` route through the plugin without any core-pipeline change.
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

def test_registry_lists_soccer():
    from sports.registry import registry
    assert "soccer" in registry.available()

def test_get_sport_soccer_returns_soccer_plugin():
    from sports import get_sport
    from sports.soccer import SoccerSport
    sport = get_sport("soccer")
    assert isinstance(sport, SoccerSport)
    assert sport.name == "soccer"

def test_get_sport_soccer_is_case_insensitive():
    from sports import get_sport
    from sports.soccer import SoccerSport
    assert isinstance(get_sport("  Soccer  "), SoccerSport)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def test_soccer_perception_prompt_mentions_soccer_terms():
    from sports.soccer.prompts import perception_prompt
    prompt = perception_prompt().lower()
    assert "offside" in prompt
    assert "penalty area" in prompt
    assert "handball" in prompt

def test_soccer_adjudicator_prompt_mentions_ifab_not_nba():
    from sports.soccer.prompts import adjudicator_prompt
    prompt = adjudicator_prompt().lower()
    assert "ifab" in prompt or "laws of the game" in prompt
    assert "nba" not in prompt

def test_catalog_resolves_real_soccer_prompt_not_stub():
    from services.analysis.prompts import _get_perception_prompt
    prompt = _get_perception_prompt("soccer").lower()
    assert "offside" in prompt
    assert "not yet configured" not in prompt

def test_plugin_prompt_matches_catalog():
    from sports import get_sport
    from services.analysis.prompts import _get_perception_prompt
    assert get_sport("soccer").perception_prompt() == _get_perception_prompt("soccer")


# ---------------------------------------------------------------------------
# Rule corpus
# ---------------------------------------------------------------------------

def test_soccer_rules_cover_supported_events():
    from rules.soccer_rules import SOCCER_RULES
    assert set(SOCCER_RULES.keys()) == {
        "foul", "offside", "handball", "penalty", "red_card", "yellow_card", "goal",
    }

def test_soccer_rule_records_have_expected_shape():
    from services.ai_analyzer import _rule_records
    records = _rule_records("soccer")
    assert len(records) == 7
    for r in records:
        assert set(r.keys()) >= {"rule_id", "section_title", "text", "call_type"}
        assert r["rule_id"] == r["rule_id"].upper()


# ---------------------------------------------------------------------------
# Detail extractor
# ---------------------------------------------------------------------------

def test_soccer_extractor_registered():
    from services.extractors import get_extractor
    from sports.soccer.extractor import SoccerDetailExtractor
    assert isinstance(get_extractor("soccer"), SoccerDetailExtractor)

def test_soccer_extractor_defaults_from_empty_perception():
    from sports.soccer.extractor import SoccerDetailExtractor
    details = SoccerDetailExtractor().extract(None, {})
    assert details.field_third == "unclear"
    assert details.in_penalty_area is False
    assert details.foul_direction == "unclear"

def test_soccer_extractor_reads_perception_fields():
    from sports.soccer.extractor import SoccerDetailExtractor
    details = SoccerDetailExtractor().extract(
        None,
        {
            "field_third": "attacking_third",
            "in_penalty_area": True,
            "offside_relevant": True,
            "last_defender": True,
            "handball_candidate": True,
            "foul_direction": "defender_on_attacker",
        },
    )
    dumped = details.model_dump()
    assert dumped["in_penalty_area"] is True
    assert dumped["field_third"] == "attacking_third"
    assert dumped["foul_direction"] == "defender_on_attacker"

def test_soccer_extractor_roundtrips_through_shared_registry():
    # The frontend sport_details block resolves the same extractor.
    from services.extractors import get_extractor
    details = get_extractor("soccer").extract(None, {"in_penalty_area": True})
    assert details.model_dump()["in_penalty_area"] is True


# ---------------------------------------------------------------------------
# Tracking evidence
# ---------------------------------------------------------------------------

def test_tracked_evidence_none_without_detections():
    from sports.soccer.tracking import summarize_tracked_evidence
    assert summarize_tracked_evidence(None) is None

def test_tracked_evidence_none_for_empty_frames():
    from sports.soccer.tracking import summarize_tracked_evidence
    assert summarize_tracked_evidence(_dets([], [])) is None

def test_tracked_evidence_derives_possession_and_direction():
    from sports.soccer.tracking import summarize_tracked_evidence
    # Player 1 carries the ball moving left-to-right across two frames.
    dets = _dets(
        [_obj("person", 0.30, 0.5, track_id=1), _obj("person", 0.60, 0.5, track_id=2), _obj("sports ball", 0.30, 0.5)],
        [_obj("person", 0.55, 0.5, track_id=1), _obj("person", 0.80, 0.5, track_id=2), _obj("sports ball", 0.55, 0.5)],
    )
    ev = summarize_tracked_evidence(dets)
    assert ev is not None
    assert ev["players_tracked"] == 2
    assert ev["frames_with_ball"] == 2
    assert ev["possession_summary"] == "in_possession"
    assert ev["attacking_direction"] == "left_to_right"
    assert 0.0 <= ev["tracking_confidence"] <= 1.0

def test_tracked_evidence_recognizes_soccer_ball_label():
    from sports.soccer.tracking import summarize_tracked_evidence
    dets = _dets([_obj("person", 0.5, 0.5, track_id=1), _obj("soccer ball", 0.5, 0.5)])
    ev = summarize_tracked_evidence(dets)
    assert ev["frames_with_ball"] == 1


# ---------------------------------------------------------------------------
# Pipeline seams — the plugin owns sport-specific behavior
# ---------------------------------------------------------------------------

def test_plugin_sport_details_none_without_detections():
    from sports import get_sport
    assert get_sport("soccer").sport_details(None, {}) is None

def test_plugin_sport_details_with_detections():
    from sports import get_sport
    dets = _dets([_obj("person", 0.5, 0.5, track_id=1), _obj("sports ball", 0.5, 0.5)])
    details = get_sport("soccer").sport_details(dets, {"in_penalty_area": True})
    assert details["in_penalty_area"] is True

def test_plugin_tracked_evidence_delegates_to_tracking():
    from sports import get_sport
    dets = _dets([_obj("person", 0.5, 0.5, track_id=1), _obj("sports ball", 0.5, 0.5)])
    ev = get_sport("soccer").tracked_evidence(dets)
    assert ev is not None and "tracking_confidence" in ev

def test_plugin_metadata_provider_is_none():
    from sports import get_sport
    assert get_sport("soccer").metadata_provider() is None

def test_mock_result_sport_field_soccer():
    from unittest.mock import MagicMock
    from services.ai_analyzer import _mock_ai_result
    result = _mock_ai_result(MagicMock(), "soccer", "", "", "", "", None, "test fallback")
    assert result["perception"]["sport"] == "soccer"

def test_frontend_perception_soccer_has_sport_details_block():
    from services.ai_analyzer import _frontend_perception
    result = _frontend_perception({"event_type": "possible_foul", "summary": "test"}, "mock", "soccer")
    assert result["sport"] == "soccer"
    assert "soccer" in result["sport_details"]
