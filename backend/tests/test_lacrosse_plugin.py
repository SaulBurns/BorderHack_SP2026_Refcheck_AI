"""Lacrosse sport plugin tests (Sprint 12 — fourth sport).

Covers the full lacrosse plugin surface: registry resolution, prompts, rule
retrieval + boosts, the detail extractor, and the tracking-evidence layer, plus
the pipeline seams (sport_details / tracked_evidence delegation) that make
``sport="lacrosse"`` route through the plugin without any core-pipeline change.
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

def test_registry_lists_lacrosse():
    from sports.registry import registry
    assert "lacrosse" in registry.available()
    assert registry.available() == ["basketball", "hockey", "lacrosse", "soccer"]

def test_get_sport_lacrosse_returns_lacrosse_plugin():
    from sports import get_sport
    from sports.lacrosse import LacrosseSport
    sport = get_sport("lacrosse")
    assert isinstance(sport, LacrosseSport)
    assert sport.name == "lacrosse"

def test_get_sport_lacrosse_is_case_insensitive():
    from sports import get_sport
    from sports.lacrosse import LacrosseSport
    assert isinstance(get_sport("  Lacrosse  "), LacrosseSport)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def test_lacrosse_perception_prompt_mentions_lacrosse_terms():
    from sports.lacrosse.prompts import perception_prompt
    prompt = perception_prompt().lower()
    assert "crease" in prompt
    assert "crosse" in prompt
    assert "midline" in prompt

def test_lacrosse_perception_prompt_avoids_basketball_geometry():
    from sports.lacrosse.prompts import perception_prompt
    assert "restricted area" not in perception_prompt().lower()

def test_lacrosse_adjudicator_prompt_mentions_ncaa_not_nba():
    from sports.lacrosse.prompts import adjudicator_prompt
    prompt = adjudicator_prompt().lower()
    assert "ncaa" in prompt
    assert "nba" not in prompt

def test_catalog_resolves_real_lacrosse_prompt_not_stub():
    from services.analysis.prompts import _get_perception_prompt
    prompt = _get_perception_prompt("lacrosse").lower()
    assert "crease" in prompt
    assert "not yet configured" not in prompt

def test_plugin_prompt_matches_catalog():
    from sports import get_sport
    from services.analysis.prompts import _get_perception_prompt
    assert get_sport("lacrosse").perception_prompt() == _get_perception_prompt("lacrosse")


# ---------------------------------------------------------------------------
# Rule corpus + retrieval boosts
# ---------------------------------------------------------------------------

def test_lacrosse_rules_cover_supported_events():
    from rules.lacrosse_rules import LACROSSE_RULES
    assert set(LACROSSE_RULES.keys()) == {
        "illegal_body_check", "slash", "push", "crease_violation", "offside", "loose_ball_push",
    }

def test_lacrosse_rule_records_have_expected_shape():
    from services.ai_analyzer import _rule_records
    records = _rule_records("lacrosse")
    assert len(records) == 6
    for r in records:
        assert set(r.keys()) >= {"rule_id", "section_title", "text", "call_type"}
        assert r["rule_id"] == r["rule_id"].upper()

@pytest.mark.parametrize(
    "rule_id,haystack,expected_positive",
    [
        ("ILLEGAL_BODY_CHECK", "body check from behind on a defenseless player head", True),
        ("SLASH", "a forceful one-handed slash with the crosse to the body", True),
        ("PUSH", "pushing pressure applied to the opponent back in possession", True),
        ("CREASE_VIOLATION", "attacker dives into the goal crease as ball crosses", True),
        ("OFFSIDE", "team failed to keep required players across the midline offside", True),
        ("LOOSE_BALL_PUSH", "pushed an opponent more than five yards from the loose ball", True),
        ("CREASE_VIOLATION", "a routine clear up the sideline", False),
    ],
)
def test_lacrosse_boosts(rule_id, haystack, expected_positive):
    from sports.lacrosse.rules import boost_rule_score
    score = boost_rule_score(rule_id, haystack)
    assert (score > 0) is expected_positive

def test_push_and_loose_ball_push_boosts_are_disjoint():
    # A loose-ball scenario must not boost PUSH; a possession push must not boost
    # LOOSE_BALL_PUSH — the two pushing rules disambiguate cleanly.
    from sports.lacrosse.rules import boost_rule_score
    loose = "pushed an opponent within five yards of the loose ball"
    possession = "pushing the ball carrier in the back"
    assert boost_rule_score("LOOSE_BALL_PUSH", loose) > 0
    assert boost_rule_score("PUSH", loose) == 0
    assert boost_rule_score("PUSH", possession) > 0
    assert boost_rule_score("LOOSE_BALL_PUSH", possession) == 0

def test_retrieve_rules_lacrosse_ranks_crease_first():
    from services.ai_analyzer import _retrieve_rules
    perception = {
        "event_type": "possible_crease_violation",
        "summary": "attacking player dives and lands in the goal crease as the ball crosses",
        "crease_violation": True,
    }
    rules = _retrieve_rules("crease violation dive goal crease goalie", perception, "lacrosse")
    assert 1 <= len(rules) <= 5
    assert rules[0]["rule_id"] == "CREASE_VIOLATION"

def test_retrieve_rules_lacrosse_ranks_illegal_body_check_first():
    from services.ai_analyzer import _retrieve_rules
    perception = {
        "event_type": "possible_illegal_body_check",
        "summary": "defenseless player hit from behind above the shoulders",
    }
    rules = _retrieve_rules("illegal body check from behind defenseless head targeting", perception, "lacrosse")
    assert rules[0]["rule_id"] == "ILLEGAL_BODY_CHECK"


# ---------------------------------------------------------------------------
# Detail extractor
# ---------------------------------------------------------------------------

def test_lacrosse_extractor_registered():
    from services.extractors import get_extractor
    from sports.lacrosse.extractor import LacrosseDetailExtractor
    assert isinstance(get_extractor("lacrosse"), LacrosseDetailExtractor)

def test_lacrosse_extractor_defaults_from_empty_perception():
    from sports.lacrosse.extractor import LacrosseDetailExtractor
    from services.perception_schema import LacrosseDetails
    # Backward-compat: empty perception yields the model defaults.
    assert LacrosseDetailExtractor().extract(None, {}) == LacrosseDetails()

def test_lacrosse_extractor_reads_perception_fields():
    from sports.lacrosse.extractor import LacrosseDetailExtractor
    details = LacrosseDetailExtractor().extract(
        None,
        {
            "crease_violation": True,
            "cross_check": True,
            "slashing": True,
            "ball_carrier_status": "loose_ball",
            "warding": True,
        },
    )
    dumped = details.model_dump()
    assert dumped["crease_violation"] is True
    assert dumped["slashing"] is True
    assert dumped["ball_carrier_status"] == "loose_ball"
    assert dumped["warding"] is True

def test_lacrosse_extractor_roundtrips_through_shared_registry():
    from services.extractors import get_extractor
    details = get_extractor("lacrosse").extract(None, {"crease_violation": True})
    assert details.model_dump()["crease_violation"] is True


# ---------------------------------------------------------------------------
# Tracking evidence
# ---------------------------------------------------------------------------

def test_tracked_evidence_none_without_detections():
    from sports.lacrosse.tracking import summarize_tracked_evidence
    assert summarize_tracked_evidence(None) is None

def test_tracked_evidence_none_for_empty_frames():
    from sports.lacrosse.tracking import summarize_tracked_evidence
    assert summarize_tracked_evidence(_dets([], [])) is None

def test_tracked_evidence_derives_possession_and_direction():
    from sports.lacrosse.tracking import summarize_tracked_evidence
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

def test_tracked_evidence_recognizes_lacrosse_ball_label():
    from sports.lacrosse.tracking import summarize_tracked_evidence
    dets = _dets([_obj("person", 0.5, 0.5, track_id=1), _obj("lacrosse ball", 0.5, 0.5)])
    ev = summarize_tracked_evidence(dets)
    assert ev["frames_with_ball"] == 1


# ---------------------------------------------------------------------------
# Pipeline seams — the plugin owns sport-specific behavior
# ---------------------------------------------------------------------------

def test_plugin_sport_details_none_without_detections():
    from sports import get_sport
    assert get_sport("lacrosse").sport_details(None, {}) is None

def test_plugin_sport_details_with_detections():
    from sports import get_sport
    dets = _dets([_obj("person", 0.5, 0.5, track_id=1), _obj("sports ball", 0.5, 0.5)])
    details = get_sport("lacrosse").sport_details(dets, {"crease_violation": True})
    assert details["crease_violation"] is True

def test_plugin_tracked_evidence_delegates_to_tracking():
    from sports import get_sport
    dets = _dets([_obj("person", 0.5, 0.5, track_id=1), _obj("sports ball", 0.5, 0.5)])
    ev = get_sport("lacrosse").tracked_evidence(dets)
    assert ev is not None and "tracking_confidence" in ev

def test_plugin_metadata_provider_is_none():
    from sports import get_sport
    assert get_sport("lacrosse").metadata_provider() is None

def test_mock_result_sport_field_lacrosse():
    from unittest.mock import MagicMock
    from services.ai_analyzer import _mock_ai_result
    result = _mock_ai_result(MagicMock(), "lacrosse", "", "", "", "", None, "test fallback")
    assert result["perception"]["sport"] == "lacrosse"

def test_frontend_perception_lacrosse_has_sport_details_block():
    from services.ai_analyzer import _frontend_perception
    result = _frontend_perception({"event_type": "possible_slash", "summary": "test"}, "mock", "", "lacrosse")
    assert result["sport"] == "lacrosse"
    assert "lacrosse" in result["sport_details"]
