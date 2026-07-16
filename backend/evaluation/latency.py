"""Inference-latency summary for the benchmarking framework (Sprint 5).

Pure functions over a list of per-clip latencies in milliseconds, so the timing
math is unit-testable in isolation from the pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LatencySummary:
    count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float
    total_ms: float

    def to_dict(self) -> dict:
        return asdict(self)


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Nearest-rank percentile (pct in [0, 100]) over an already-sorted list."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = pct / 100 * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * frac


def summarize_latencies(latencies_ms: list[float]) -> LatencySummary:
    """Mean / p50 / p95 / min / max / total over per-clip latencies (ms)."""
    if not latencies_ms:
        return LatencySummary(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    ordered = sorted(latencies_ms)
    total = sum(ordered)
    return LatencySummary(
        count=len(ordered),
        mean_ms=round(total / len(ordered), 3),
        p50_ms=round(_percentile(ordered, 50), 3),
        p95_ms=round(_percentile(ordered, 95), 3),
        min_ms=round(ordered[0], 3),
        max_ms=round(ordered[-1], 3),
        total_ms=round(total, 3),
    )
