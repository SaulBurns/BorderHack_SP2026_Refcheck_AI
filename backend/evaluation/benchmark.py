"""Automated benchmarking + provider comparison (Sprint 5).

Runs a labeled dataset through the real pipeline once per provider (mock,
anthropic, gemini), measuring inference latency, and packages each run's
EvaluationReport + LatencySummary into a BenchmarkReport for side-by-side
comparison. Report rendering (Markdown/HTML) lives in evaluation.report.

The pipeline is reached through `collect_predictions` in evaluation.cli, so the
provider seam, env handling, and per-clip prediction logic are shared with the
single-provider runner (no duplication). Tests inject `analyze_fn` to run fully
offline and deterministically.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
from evaluation.latency import LatencySummary, summarize_latencies
from evaluation.runner import EvaluationReport, evaluate_predictions
from services import config


@dataclass(frozen=True)
class BenchmarkResult:
    """One provider's run over the dataset: accuracy metrics + latency."""

    provider: str
    detector: str
    evaluation: EvaluationReport
    latency: LatencySummary

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "detector": self.detector,
            "evaluation": self.evaluation.to_dict(),
            "latency": self.latency.to_dict(),
        }


@dataclass(frozen=True)
class BenchmarkReport:
    """Provider comparison over a single dataset."""

    dataset: str
    detector: str
    generated_at: str
    clip_count: int
    results: list[BenchmarkResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "detector": self.detector,
            "generated_at": self.generated_at,
            "clip_count": self.clip_count,
            "results": [result.to_dict() for result in self.results],
        }


def run_benchmark(
    dataset_path: str | Path,
    providers: list[str],
    detector: str = config.DEFAULT_DETECTOR,
    analyze_fn: AnalyzeFn | None = None,
) -> BenchmarkReport:
    """Benchmark every provider over the dataset and return a comparison report."""
    if not providers:
        raise ValueError("At least one provider is required for a benchmark.")
    unknown = [p for p in providers if p not in PROVIDERS]
    if unknown:
        raise ValueError(f"Unknown provider(s) {unknown}; expected from {PROVIDERS}.")
    if detector not in DETECTORS:
        raise ValueError(f"Unknown detector {detector!r}; expected one of {DETECTORS}.")

    analyze_fn = _resolve_analyze_fn(analyze_fn)
    labeled, run_params_by_id = _load_dataset(dataset_path)

    results: list[BenchmarkResult] = []
    for provider in providers:
        predictions, latencies_ms = collect_predictions(
            labeled, run_params_by_id, provider, detector, analyze_fn
        )
        results.append(
            BenchmarkResult(
                provider=provider,
                detector=detector,
                evaluation=evaluate_predictions(labeled, predictions),
                latency=summarize_latencies(latencies_ms),
            )
        )

    return BenchmarkReport(
        dataset=str(dataset_path),
        detector=detector,
        generated_at=datetime.now(timezone.utc).isoformat(),
        clip_count=len(labeled),
        results=results,
    )
