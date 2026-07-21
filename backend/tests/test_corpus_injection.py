"""Sprint 16A — rule-corpus injection regression tests.

The Retrieval agent was removed; the pipeline now injects each sport's *complete*
rule corpus straight into both adjudicator prompts. These tests lock that in:

1. Every rule in ``_rule_records(sport)`` appears in the adjudicator prompt.
2. Running the pipeline, both adjudicators receive the identical prompt carrying
   the whole corpus.
3. An unregistered sport (GenericSport) has an empty corpus and still adjudicates
   without crashing (Claude-only fallback).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import services.ai_analyzer as ai
from services.ai_analyzer import _build_adjudicator_prompt, _rule_records, _run_four_agent_pipeline
from services.detectors.detection_models import DetectorResult

_REGISTERED_SPORTS = ("basketball", "soccer", "hockey", "lacrosse")


# ---------------------------------------------------------------------------
# 1. The whole corpus lands in the adjudicator prompt
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sport", _REGISTERED_SPORTS)
def test_full_corpus_present_in_adjudicator_prompt(sport):
    rules = list(_rule_records(sport))
    assert rules, f"{sport} should have a non-empty corpus"
    prompt = _build_adjudicator_prompt(
        perception={"summary": "a play", "event_type": "unclear"},
        rules=rules,
        original_call="foul",
    )
    # Every rule id AND its section title (the rule text) is injected — not a
    # retrieved subset.
    for rule in rules:
        assert rule["rule_id"] in prompt, f"{rule['rule_id']} missing from {sport} prompt"
        assert rule["section_title"] in prompt
    assert "SPORT RULEBOOK" in prompt


@pytest.mark.parametrize(
    "sport,expected_count",
    [("basketball", 9), ("soccer", 7), ("hockey", 7), ("lacrosse", 6)],
)
def test_corpus_counts_match_rulebooks(sport, expected_count):
    assert len(_rule_records(sport)) == expected_count


# ---------------------------------------------------------------------------
# 2. Pipeline: both adjudicators receive the identical, complete corpus
# ---------------------------------------------------------------------------

def _pipeline(monkeypatch, sport):
    seen = []

    class _FakeDetector:
        name = "fake"
        def detect(self, frames, sport, original_call):
            return DetectorResult(
                perception={"sport": sport, "event_type": "unclear"}, detections=None
            )

    def fake_adjudicator(*, user_prompt, framing, temperature, sport):
        seen.append(user_prompt)
        return {"verdict": "inconclusive", "confidence": 0.5}

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setattr(ai, "get_detector", lambda name=None: _FakeDetector())
    monkeypatch.setattr(ai, "_adjudicator_agent", fake_adjudicator)

    _run_four_agent_pipeline(
        frame_paths=[Path("f.jpg")],
        file=MagicMock(),
        sport=sport,
        level_of_play="",
        league="",
        original_call="",
        referee_name="",
        video_metadata=None,
    )
    return seen


def test_pipeline_injects_full_corpus_into_both_adjudicators(monkeypatch):
    seen = _pipeline(monkeypatch, "basketball")
    assert len(seen) == 2                      # both adjudicators ran
    assert seen[0] == seen[1]                   # identical prompt (built once)
    for rule in _rule_records("basketball"):
        assert rule["rule_id"] in seen[0]


# ---------------------------------------------------------------------------
# 3. Unregistered sport (GenericSport): empty corpus, still adjudicates
# ---------------------------------------------------------------------------

def test_unregistered_sport_has_empty_corpus():
    assert _rule_records("curling") == ()


def test_unregistered_sport_still_adjudicates(monkeypatch):
    seen = _pipeline(monkeypatch, "curling")
    assert len(seen) == 2                        # adjudicators still ran (no crash)
    assert "SPORT RULEBOOK" in seen[0]           # header present, corpus body empty
