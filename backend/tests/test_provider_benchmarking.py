"""Sprint 17D — provider benchmarking (Claude vs Gemini vs mixed routing).

Covers the token-usage recorder, the pricing/cost model, provider combos, and the
end-to-end benchmark that measures accuracy + latency + tokens + estimated cost per
combo, plus the tokens/cost columns in the rendered reports.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from evaluation import cost as cost_mod
from evaluation.benchmark import (
    STANDARD_COMBOS,
    BenchmarkReport,
    ProviderCombo,
    resolve_combo,
    run_benchmark,
)
from evaluation.report import render_html, render_markdown
from services.ai import usage


@pytest.fixture(autouse=True)
def _reset_usage():
    usage.disable()
    usage.reset()
    yield
    usage.disable()
    usage.reset()


# ---------------------------------------------------------------------------
# Token estimation + recorder
# ---------------------------------------------------------------------------

def test_estimate_tokens_ceil_division():
    assert usage.estimate_tokens("") == 0
    assert usage.estimate_tokens("abcd") == 1       # 4 chars / 4
    assert usage.estimate_tokens("abcde") == 2      # ceil(5 / 4)


def test_estimate_content_tokens_counts_images_flat():
    content = [{"type": "image", "path": "a.jpg"}, {"type": "text", "text": "abcd"}]
    assert usage.estimate_content_tokens(content) == usage.IMAGE_TOKEN_ESTIMATE + 1


def test_record_is_noop_until_enabled():
    usage.record("anthropic", "claude-sonnet-4-5", 100, 50)
    assert usage.snapshot()["calls"] == 0  # disabled → nothing recorded


def test_record_aggregates_by_model_when_enabled():
    usage.enable()
    usage.record("gemini", "gemini-2.5-flash", 100, 50)
    usage.record("gemini", "gemini-2.5-flash", 200, 60)
    snap = usage.snapshot()
    assert snap["calls"] == 2
    assert snap["prompt_tokens"] == 300 and snap["completion_tokens"] == 110
    assert snap["total_tokens"] == 410
    assert snap["by_model"]["gemini-2.5-flash"]["provider"] == "gemini"


def test_record_call_estimates_from_text():
    usage.enable()
    usage.record_call(
        provider="gemini", model="gemini-2.5-flash",
        system_prompt="abcd", user_content="abcdefgh", reply="ab",
    )
    snap = usage.snapshot()["by_model"]["gemini-2.5-flash"]
    assert snap["prompt_tokens"] == 1 + 2  # "abcd"=1, "abcdefgh"=2
    assert snap["completion_tokens"] == 1  # "ab"=ceil(2/4)=1


# ---------------------------------------------------------------------------
# Pricing / cost model
# ---------------------------------------------------------------------------

def test_price_for_known_and_unknown():
    assert cost_mod.price_for("claude-sonnet-4-5") == (3.00, 15.00)
    assert cost_mod.price_for("gemini-2.5-flash") == (0.30, 2.50)
    assert cost_mod.price_for("nonexistent-model") is None


def test_cost_for_model():
    # 1M input @ $3 + 1M output @ $15 = $18.
    assert cost_mod.cost_for_model("claude-sonnet-4-5", 1_000_000, 1_000_000) == pytest.approx(18.0)
    # Unknown model → free (never guesses a price).
    assert cost_mod.cost_for_model("mystery", 1_000_000, 0) == 0.0


def test_cost_summary_from_snapshot():
    snap = {"by_model": {"gemini-2.5-flash": {"prompt_tokens": 1_000_000, "completion_tokens": 0}}}
    summary = cost_mod.CostSummary.from_usage_snapshot(snap)
    assert summary.total_usd == pytest.approx(0.30)
    assert summary.by_model["gemini-2.5-flash"]["priced"] is True
    assert summary.estimated is True


# ---------------------------------------------------------------------------
# Provider combos
# ---------------------------------------------------------------------------

def test_resolve_combo_named():
    assert resolve_combo("claude").env["AI_PROVIDER"] == "anthropic"
    assert resolve_combo("gemini").env["AI_PROVIDER"] == "gemini"
    mixed = resolve_combo("mixed")
    assert mixed.env["AI_PROVIDER"] == "router"
    assert mixed.env["PERCEPTION_PROVIDER"] == "gemini"
    assert mixed.env["ADJUDICATOR_PROVIDER"] == "anthropic"


def test_resolve_combo_bare_provider_backward_compatible():
    assert resolve_combo("mock").env == {"AI_PROVIDER": "mock"}
    assert resolve_combo("anthropic").env == {"AI_PROVIDER": "anthropic"}


def test_resolve_combo_unknown_raises():
    with pytest.raises(ValueError, match="Unknown provider/combo"):
        resolve_combo("openai")


# ---------------------------------------------------------------------------
# End-to-end benchmark: accuracy + latency + tokens + cost per combo
# ---------------------------------------------------------------------------

def _write_dataset(tmp_path):
    rows = [
        {"clip_id": "c1", "sport": "basketball", "ground_truth_verdict": "fair_call"},
        {"clip_id": "c2", "sport": "basketball", "ground_truth_verdict": "fair_call"},
    ]
    path = tmp_path / "ds.json"
    path.write_text(json.dumps(rows))
    return path


def _analyze_with_usage(**kwargs):
    """Fake pipeline that records provider-specific token usage (as the real
    `_call_provider` would) so the benchmark can measure tokens/cost offline."""
    provider = os.environ.get("AI_PROVIDER", "mock")
    if provider == "anthropic":
        usage.record("anthropic", "claude-sonnet-4-5", 1000, 200)
    elif provider == "gemini":
        usage.record("gemini", "gemini-2.5-flash", 1000, 200)
    elif provider == "router":  # mixed: perception→gemini, adjudication→anthropic
        usage.record("gemini", "gemini-2.5-flash", 800, 100)
        usage.record("anthropic", "claude-sonnet-4-5", 1200, 250)
    return {"clip_id": "hash", "verdict": {"verdict": "fair_call", "confidence": 0.8}}


def test_benchmark_measures_tokens_and_cost_per_combo(tmp_path):
    ds = _write_dataset(tmp_path)
    report = run_benchmark(ds, ["claude", "gemini", "mixed", "mock"], analyze_fn=_analyze_with_usage)
    by = {r.provider: r for r in report.results}

    # Claude: 2 clips × (1000 prompt + 200 completion).
    assert by["claude"].usage.total_tokens == 2 * 1200
    assert by["claude"].cost.total_usd > 0

    # Gemini is cheaper than Claude for the same token volume.
    assert by["gemini"].cost.total_usd < by["claude"].cost.total_usd

    # Mixed routing splits tokens across BOTH models.
    assert set(by["mixed"].usage.by_model) == {"gemini-2.5-flash", "claude-sonnet-4-5"}

    # Mock is free/offline — no tokens recorded, zero cost.
    assert by["mock"].usage.total_tokens == 0
    assert by["mock"].cost.total_usd == 0.0

    # The cheapest *priced* combo is gemini.
    assert report.cheapest_provider() == "gemini"

    # Usage tracking is turned back off after the benchmark (no leakage).
    assert usage.is_enabled() is False


def test_benchmark_result_dict_has_usage_and_cost(tmp_path):
    ds = _write_dataset(tmp_path)
    report = run_benchmark(ds, ["gemini"], analyze_fn=_analyze_with_usage)
    result = report.to_dict()["results"][0]
    assert "usage" in result and "cost" in result
    assert result["usage"]["total_tokens"] == 2 * 1200
    assert report.to_dict()["cheapest_provider"] == "gemini"


# ---------------------------------------------------------------------------
# Reports expose the new columns
# ---------------------------------------------------------------------------

def test_reports_include_tokens_and_cost(tmp_path):
    ds = _write_dataset(tmp_path)
    report = run_benchmark(ds, ["claude", "gemini"], analyze_fn=_analyze_with_usage)
    md = render_markdown(report)
    assert "| Tokens | Cost (USD) |" in md
    assert "Lowest estimated cost:" in md
    assert "Est. cost:" in md
    html = render_html(report)
    assert "Cost (USD)" in html
    assert "Tokens" in html
