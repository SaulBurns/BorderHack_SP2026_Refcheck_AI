"""Sprint 14 — Model Improvements: unit tests for the AI-quality changes.

Covers: confidence calibration, provider-optimization request builders (Claude
prompt cache, Gemini JSON mode), and the evaluation metrics (Brier, MCC) +
provider recommendation.

Note: two blocks of tests were removed as their features were retired —
(1) the sport-agnostic retrieval query builder + field-weighted retrieval scoring
(Sprint 16A, retrieval stage removed), and (2) the `<thinking>` chain-of-thought
isolation in `_extract_json` (Sprint 16B, regex extraction replaced by
structured outputs + Pydantic validation — see `test_structured_outputs.py`).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


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
