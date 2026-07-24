"""Automated benchmarking + provider comparison (Sprint 5; extended Sprint 17D).

Runs a labeled dataset through the real pipeline once per **provider combination**
and packages each run's accuracy metrics + latency + token usage + estimated cost
into a BenchmarkReport for side-by-side comparison. Report rendering (Markdown/HTML)
lives in evaluation.report.

Sprint 17D — the benchmarkable unit is a `ProviderCombo`, not just a single
provider. Beyond the plain providers (`mock`/`anthropic`/`gemini`), named combos
compare the three deployment shapes the project ships:
  - `claude`  → AI_PROVIDER=anthropic
  - `gemini`  → AI_PROVIDER=gemini
  - `mixed`   → AI_PROVIDER=router, perception→gemini, adjudication→anthropic
Each combo run also measures token usage (via `services.ai.usage`) and estimated
cost (via `evaluation.cost`), so the report answers accuracy **and** cost/tokens.

The pipeline is reached through `collect_predictions` in evaluation.cli, so the
provider seam, env handling, and per-clip prediction logic are shared with the
single-provider runner (no duplication). Tests inject `analyze_fn` to run offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from evaluation.cli import (
    DETECTORS,
    PROVIDERS,
    AnalyzeFn,
    _load_dataset,
    _resolve_analyze_fn,
    collect_predictions,
)
from evaluation.cost import CostSummary, TokenUsage
from evaluation.latency import LatencySummary, summarize_latencies
from evaluation.runner import EvaluationReport, evaluate_predictions
from services import config
from services.ai import usage as _usage


@dataclass(frozen=True)
class ProviderCombo:
    """A named benchmark configuration: a label + the env vars it runs under.

    `env` always includes `AI_PROVIDER`; mixed routing adds the per-stage vars.
    """

    name: str
    env: dict[str, str] = field(default_factory=dict)

    @property
    def provider(self) -> str:
        return self.env.get("AI_PROVIDER", "mock")


# The comparison set for Sprint 17D — Claude vs Gemini vs mixed routing (+ mock
# as the free offline baseline). Mixed reuses the Sprint 17B router seam.
STANDARD_COMBOS: dict[str, ProviderCombo] = {
    "mock": ProviderCombo("mock", {"AI_PROVIDER": "mock"}),
    "claude": ProviderCombo("claude", {"AI_PROVIDER": "anthropic"}),
    "gemini": ProviderCombo("gemini", {"AI_PROVIDER": "gemini"}),
    "mixed": ProviderCombo(
        "mixed",
        {
            "AI_PROVIDER": "router",
            "PERCEPTION_PROVIDER": "gemini",
            "PERCEPTION_MODEL": config.DEFAULT_GEMINI_MODEL,
            "ADJUDICATOR_PROVIDER": "anthropic",
            "ADJUDICATOR_MODEL": config.DEFAULT_ANTHROPIC_MODEL,
        },
    ),
}


def resolve_combo(name: str) -> ProviderCombo:
    """Resolve a combo name (`claude`/`gemini`/`mixed`) or a bare provider name.

    A bare provider (`mock`/`anthropic`/`gemini`) resolves to a single-provider
    combo — backward compatible with the Sprint 5 `run_benchmark(providers=...)`.
    """
    if name in STANDARD_COMBOS:
        return STANDARD_COMBOS[name]
    if name in PROVIDERS:
        return ProviderCombo(name, {"AI_PROVIDER": name})
    raise ValueError(
        f"Unknown provider/combo {name!r}; expected one of "
        f"{sorted(set(PROVIDERS) | set(STANDARD_COMBOS))}."
    )


def _empty_usage() -> TokenUsage:
    return TokenUsage.from_snapshot({})


def _empty_cost() -> CostSummary:
    return CostSummary.from_usage_snapshot({})


@dataclass(frozen=True)
class BenchmarkResult:
    """One combo's run over the dataset: accuracy + latency + tokens + cost.

    `usage`/`cost` default to empty (Sprint 17D added them) so pre-17D construction
    — e.g. building a result with only accuracy + latency — stays valid.
    """

    provider: str
    detector: str
    evaluation: EvaluationReport
    latency: LatencySummary
    usage: TokenUsage = field(default_factory=_empty_usage)
    cost: CostSummary = field(default_factory=_empty_cost)

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "detector": self.detector,
            "evaluation": self.evaluation.to_dict(),
            "latency": self.latency.to_dict(),
            "usage": self.usage.to_dict(),
            "cost": self.cost.to_dict(),
        }


@dataclass(frozen=True)
class BenchmarkReport:
    """Provider comparison over a single dataset."""

    dataset: str
    detector: str
    generated_at: str
    clip_count: int
    results: list[BenchmarkResult] = field(default_factory=list)

    def recommended_provider(self) -> str | None:
        """The best provider by a principled, quality-first ranking (Sprint 14).

        Ordered by: highest accuracy, then highest Matthews correlation (robust to
        class imbalance), then lowest Brier score (best-calibrated confidence), then
        lowest p50 latency as the final tiebreaker. Returns None for an empty report.
        """
        if not self.results:
            return None
        best = max(
            self.results,
            key=lambda r: (
                r.evaluation.accuracy,
                r.evaluation.mcc,
                -r.evaluation.brier,
                -r.latency.p50_ms,
            ),
        )
        return best.provider

    def cheapest_provider(self) -> str | None:
        """The lowest estimated-cost combo among those that spent anything (Sprint 17D).

        Ignores zero-cost runs (mock / offline degradation) so the callout reflects
        a real cost comparison; None when no combo recorded a cost.
        """
        priced = [r for r in self.results if r.cost.total_usd > 0]
        if not priced:
            return None
        return min(priced, key=lambda r: r.cost.total_usd).provider

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "detector": self.detector,
            "generated_at": self.generated_at,
            "clip_count": self.clip_count,
            "recommended_provider": self.recommended_provider(),
            "cheapest_provider": self.cheapest_provider(),
            "results": [result.to_dict() for result in self.results],
        }


def run_benchmark(
    dataset_path: str | Path,
    providers: list[str],
    detector: str = config.DEFAULT_DETECTOR,
    analyze_fn: AnalyzeFn | None = None,
) -> BenchmarkReport:
    """Benchmark every provider/combo over the dataset and return a comparison report.

    `providers` accepts bare provider names (`mock`/`anthropic`/`gemini`) and named
    combos (`claude`/`gemini`/`mixed`); each is resolved to a `ProviderCombo`.
    """
    if not providers:
        raise ValueError("At least one provider is required for a benchmark.")
    combos = [resolve_combo(name) for name in providers]  # raises on unknown names
    if detector not in DETECTORS:
        raise ValueError(f"Unknown detector {detector!r}; expected one of {DETECTORS}.")

    analyze_fn = _resolve_analyze_fn(analyze_fn)
    labeled, run_params_by_id = _load_dataset(dataset_path)

    results: list[BenchmarkResult] = []
    _usage.enable()
    try:
        for combo in combos:
            _usage.reset()
            predictions, latencies_ms = collect_predictions(
                labeled, run_params_by_id, combo.provider, detector, analyze_fn, env=combo.env
            )
            snapshot = _usage.snapshot()
            results.append(
                BenchmarkResult(
                    provider=combo.name,
                    detector=detector,
                    evaluation=evaluate_predictions(labeled, predictions),
                    latency=summarize_latencies(latencies_ms),
                    usage=TokenUsage.from_snapshot(snapshot),
                    cost=CostSummary.from_usage_snapshot(snapshot),
                )
            )
    finally:
        _usage.disable()
        _usage.reset()

    return BenchmarkReport(
        dataset=str(dataset_path),
        detector=detector,
        generated_at=datetime.now(timezone.utc).isoformat(),
        clip_count=len(labeled),
        results=results,
    )
