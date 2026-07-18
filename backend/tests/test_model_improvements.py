"""Sprint 14 — Model Improvements: unit tests for the AI-quality changes.

Covers: chain-of-thought isolation in JSON extraction, the sport-agnostic
retrieval query builder, field-weighted retrieval scoring, confidence calibration,
provider-optimization request builders (Claude prompt cache, Gemini JSON mode),
and the new evaluation metrics (Brier, MCC) + provider recommendation.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# Chain-of-thought isolation (_extract_json)
# ---------------------------------------------------------------------------

from services.ai_analyzer import _extract_json


def test_extract_plain_json():
    assert _extract_json('{"verdict": "fair_call"}') == {"verdict": "fair_call"}

def test_extract_strips_thinking_block_before_json():
    raw = '<thinking>The defender was set {this is not json}</thinking>\n{"verdict": "bad_call", "confidence": 0.7}'
    assert _extract_json(raw) == {"verdict": "bad_call", "confidence": 0.7}

def test_extract_ignores_braces_inside_scratchpad():
    # A brace-containing scratchpad must not corrupt parsing of the real JSON.
    raw = '<scratchpad>consider {"verdict": "WRONG"}</scratchpad> {"verdict": "fair_call"}'
    assert _extract_json(raw) == {"verdict": "fair_call"}

def test_extract_prefers_fenced_json_block():
    raw = "Sure!\n```json\n{\"verdict\": \"inconclusive\"}\n```\nHope that helps."
    assert _extract_json(raw) == {"verdict": "inconclusive"}

def test_extract_falls_back_to_outermost_braces():
    raw = 'Here is the verdict: {"verdict": "bad_call"} — thanks'
    assert _extract_json(raw) == {"verdict": "bad_call"}

def test_extract_raises_on_no_json():
    with pytest.raises(Exception):
        _extract_json("no json here at all")


# ---------------------------------------------------------------------------
# Sport-agnostic retrieval query builder (_build_retrieval_prompt)
# ---------------------------------------------------------------------------

from services.ai_analyzer import _build_retrieval_prompt


def test_retrieval_prompt_includes_sport_and_core_fields():
    prompt = _build_retrieval_prompt(
        {"event_type": "possible_penalty", "summary": "trip in the box", "contact_detected": True},
        "soccer",
    )
    assert "Sport: soccer" in prompt
    assert "possible_penalty" in prompt
    assert "trip in the box" in prompt

def test_retrieval_prompt_flattens_sport_details_and_skips_basketball_labels():
    prompt = _build_retrieval_prompt(
        {
            "event_type": "possible_penalty",
            "summary": "foul",
            "sport_details": {
                "soccer": {
                    "field_third": "attacking_third",
                    "in_penalty_area": True,
                    "offside_relevant": False,
                    "foul_direction": "unclear",
                }
            },
        },
        "soccer",
    )
    assert "In penalty area: True" in prompt
    assert "Field third: attacking_third" in prompt
    # False / "unclear" values are skipped, and basketball-only labels never appear.
    assert "Offside relevant" not in prompt
    assert "Foul direction" not in prompt
    assert "Legal guarding position" not in prompt
    assert "Court zone" not in prompt

def test_retrieval_prompt_flattens_nested_basketball_details():
    prompt = _build_retrieval_prompt(
        {
            "event_type": "possible_charge",
            "summary": "contact at the rim",
            "sport_details": {
                "basketball": {
                    "offensive_control_status": "airborne_shooter",
                    "defender_status": {"legal_guarding_position": "established"},
                }
            },
        },
        "basketball",
    )
    assert "Offensive control status: airborne_shooter" in prompt
    assert "Legal guarding position: established" in prompt


# ---------------------------------------------------------------------------
# Field-weighted retrieval scoring
# ---------------------------------------------------------------------------

from services.analysis.retrieval import _tokens, _keyword_score, _LABEL_WEIGHT, _BODY_WEIGHT


def test_tokens_drops_stopwords_and_short_noise():
    assert _tokens("The defender was in the restricted area") == ["defender", "restricted", "area"]

def test_keyword_score_weights_label_match_above_body():
    rule = {
        "rule_id": "OFFSIDE",
        "section_title": "Offside offence",
        "call_type": "Offside",
        "text": "A player interfering with an opponent while beyond the last defender.",
    }
    # "offside" is only in the label fields -> label weight.
    label_only = _keyword_score(frozenset(["offside"]), rule)
    # "opponent" is only in the body -> body weight.
    body_only = _keyword_score(frozenset(["opponent"]), rule)
    assert label_only == _LABEL_WEIGHT
    assert body_only == _BODY_WEIGHT
    assert label_only > body_only

def test_keyword_score_ignores_non_matching_terms():
    rule = {"rule_id": "GOAL", "section_title": "Goal", "call_type": "Goal", "text": "ball over the line"}
    assert _keyword_score(frozenset(["tripping", "handball"]), rule) == 0


# ---------------------------------------------------------------------------
# Confidence calibration
# ---------------------------------------------------------------------------

from services.analysis.calibration import calibrate_confidence, quality_retention


def test_calibration_identity_for_clear():
    assert calibrate_confidence(0.83, "clear") == 0.83

def test_calibration_shrinks_overconfidence_on_partial():
    assert calibrate_confidence(0.8, "partial") == pytest.approx(0.5 + 0.85 * 0.3)
    assert calibrate_confidence(0.8, "partial") < 0.8

def test_calibration_pulls_underconfidence_up_toward_prior():
    assert calibrate_confidence(0.2, "partial") > 0.2

def test_calibration_is_bounded():
    assert 0.0 <= calibrate_confidence(1.0, "poor") <= 1.0
    assert 0.0 <= calibrate_confidence(0.0, "poor") <= 1.0

def test_calibration_unknown_quality_uses_default_retention():
    assert quality_retention("banana") == quality_retention("partial")


# ---------------------------------------------------------------------------
# Provider optimization — request builders (pure, no network / SDK)
# ---------------------------------------------------------------------------

from services.ai.providers.anthropic_provider import AnthropicProvider
from services.ai.providers.gemini_provider import GeminiProvider


def _payload(prompt_cache):
    return AnthropicProvider.build_payload(
        model="claude-x", system_prompt="SYS", blocks=[{"type": "text", "text": "hi"}],
        temperature=0.2, max_tokens=100, prompt_cache=prompt_cache,
    )

def test_anthropic_payload_default_uses_plain_string_system():
    payload = _payload(False)
    assert payload["system"] == "SYS"
    assert payload["model"] == "claude-x"
    assert payload["messages"][0]["content"] == [{"type": "text", "text": "hi"}]

def test_anthropic_payload_prompt_cache_marks_system_block():
    payload = _payload(True)
    assert payload["system"] == [
        {"type": "text", "text": "SYS", "cache_control": {"type": "ephemeral"}}
    ]

def test_gemini_kwargs_default_has_no_json_mime():
    kwargs = GeminiProvider.generation_kwargs(
        system_prompt="SYS", temperature=0.3, max_tokens=200, json_mode=False
    )
    assert kwargs["system_instruction"] == "SYS"
    assert kwargs["max_output_tokens"] == 200
    assert "response_mime_type" not in kwargs

def test_gemini_kwargs_json_mode_sets_mime():
    kwargs = GeminiProvider.generation_kwargs(
        system_prompt="SYS", temperature=0.3, max_tokens=200, json_mode=True
    )
    assert kwargs["response_mime_type"] == "application/json"


# ---------------------------------------------------------------------------
# Evaluation metrics — Brier, MCC, provider recommendation
# ---------------------------------------------------------------------------

from evaluation.metrics import brier_score, matthews_corrcoef
from evaluation.models import EvaluationRecord


def _rec(gt, pred, conf):
    return EvaluationRecord(clip_id="c", ground_truth=gt, predicted=pred, confidence=conf)

def test_brier_score_zero_for_perfectly_calibrated():
    # Correct with confidence 1.0, incorrect with confidence 0.0 -> 0 error.
    records = [_rec("fair_call", "fair_call", 1.0), _rec("bad_call", "fair_call", 0.0)]
    assert brier_score(records) == 0.0

def test_brier_score_penalizes_confident_mistakes():
    confident_wrong = [_rec("bad_call", "fair_call", 1.0)]
    assert brier_score(confident_wrong) == 1.0

def test_brier_empty_is_zero():
    assert brier_score([]) == 0.0

def test_mcc_perfect_agreement_is_one():
    records = [_rec("fair_call", "fair_call", 1.0), _rec("bad_call", "bad_call", 1.0)]
    assert matthews_corrcoef(records) == pytest.approx(1.0)

def test_mcc_single_class_is_zero():
    # No variance in predictions -> undefined -> defined as 0.
    records = [_rec("fair_call", "fair_call", 1.0), _rec("bad_call", "fair_call", 1.0)]
    assert matthews_corrcoef(records) == 0.0

def test_evaluation_report_exposes_brier_and_mcc():
    from evaluation.runner import evaluate
    report = evaluate([_rec("fair_call", "fair_call", 0.9), _rec("bad_call", "bad_call", 0.8)])
    assert report.brier == pytest.approx((0.1**2 + 0.2**2) / 2)
    assert report.mcc == pytest.approx(1.0)
    assert "brier" in report.to_dict() and "mcc" in report.to_dict()


def test_recommended_provider_prefers_accuracy_then_calibration():
    from evaluation.benchmark import BenchmarkReport, BenchmarkResult
    from evaluation.runner import evaluate
    from evaluation.latency import summarize_latencies

    strong = BenchmarkResult(
        provider="anthropic", detector="claude_vision",
        evaluation=evaluate([_rec("fair_call", "fair_call", 0.9), _rec("bad_call", "bad_call", 0.9)]),
        latency=summarize_latencies([100.0]),
    )
    weak = BenchmarkResult(
        provider="mock", detector="claude_vision",
        evaluation=evaluate([_rec("fair_call", "bad_call", 0.9), _rec("bad_call", "bad_call", 0.9)]),
        latency=summarize_latencies([10.0]),
    )
    report = BenchmarkReport(
        dataset="d", detector="claude_vision", generated_at="t", clip_count=2,
        results=[weak, strong],
    )
    assert report.recommended_provider() == "anthropic"
    assert report.to_dict()["recommended_provider"] == "anthropic"
