"""Offline performance benchmark for the four-agent pipeline (Sprint 6).

Exercises the *real* orchestration (`analyze_clip`) without any network by
injecting a simulated-latency provider. This makes the effect of the Sprint 6
optimizations measurable and repeatable on any machine:

  * ``--delay 0``    isolates pure-Python orchestration overhead (rule-record
                     rebuilds, provider instantiation, frame re-extraction, JSON
                     serialization). This is where caching / dedup shows up.
  * ``--delay 0.5``  simulates network-bound model calls. This is where
                     parallelizing the two adjudicators shows up: sequential
                     costs ~2x delay, parallel costs ~1x delay per analysis.

It counts provider ``send_messages`` calls per analysis so the "reduce duplicate
Claude requests" goal is directly observable, and times cold vs warm frame
extraction so the frame cache is visible.

Usage:
    python scripts/perf_benchmark.py --iterations 5 --delay 0.5 --output before.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import threading
from pathlib import Path
from time import perf_counter, sleep
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ai.provider import AIProvider, MessageContent

# A perception/adjudicator-shaped JSON blob valid for every agent's parser:
# perception reads it with .get() defaults; the adjudicators read verdict/
# confidence. visual_quality/perception_confidence are set so reconciliation
# does not short-circuit to "inconclusive".
_BENCH_REPLY = json.dumps(
    {
        "sport": "basketball",
        "event_type": "possible_blocking_foul",
        "summary": "Benchmark synthetic play.",
        "visual_quality": "clear",
        "perception_confidence": 0.8,
        "verdict": "fair_call",
        "confidence": 0.8,
        "primary_rule_id": "BLOCK_CHARGE",
        "supporting_rule_ids": [],
        "reasoning": "Benchmark reasoning.",
        "flags": [],
    }
)


class _BenchProvider(AIProvider):
    """Non-mock provider that sleeps `delay_s` and returns valid JSON.

    Thread-safe call counter so we can report provider calls per analysis and
    verify concurrent adjudication actually overlaps.
    """

    _lock = threading.Lock()
    calls = 0
    max_concurrent = 0
    _active = 0

    def __init__(self, delay_s: float = 0.0) -> None:
        self.delay_s = delay_s

    def provider_name(self) -> str:
        return "bench"

    def supports_vision(self) -> bool:
        return True

    def send_messages(self, *, system_prompt, user_content: MessageContent, temperature, max_tokens=1200) -> str:
        with _BenchProvider._lock:
            _BenchProvider.calls += 1
            _BenchProvider._active += 1
            _BenchProvider.max_concurrent = max(_BenchProvider.max_concurrent, _BenchProvider._active)
        if self.delay_s:
            sleep(self.delay_s)
        with _BenchProvider._lock:
            _BenchProvider._active -= 1
        return _BENCH_REPLY

    @classmethod
    def reset(cls) -> None:
        cls.calls = 0
        cls.max_concurrent = 0
        cls._active = 0


def _make_file() -> SimpleNamespace:
    return SimpleNamespace(filename="bench_clip.mp4", content_type="video/mp4")


def _video_metadata(clip_path: Path) -> dict:
    return {"stored_path": str(clip_path), "size_bytes": clip_path.stat().st_size}


def _pctl(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round((p / 100.0) * (len(ordered) - 1))))
    return ordered[idx]


def run_benchmark(clip_path: Path, iterations: int, delay: float) -> dict:
    import services.ai_analyzer as analyzer

    provider = _BenchProvider(delay_s=delay)
    original_get_provider = analyzer.get_provider
    analyzer.get_provider = lambda *a, **k: provider  # type: ignore[assignment]
    # Reset any cached provider the analyzer may hold (post-optimization).
    if hasattr(analyzer, "_reset_provider_cache"):
        analyzer._reset_provider_cache()

    video_metadata = _video_metadata(clip_path)
    durations: list[float] = []
    calls_per_analysis: list[int] = []
    try:
        for _ in range(iterations):
            _BenchProvider.reset()
            started = perf_counter()
            analyzer.analyze_clip(
                file=_make_file(),
                sport="basketball",
                original_call="blocking foul",
                video_metadata=video_metadata,
            )
            durations.append((perf_counter() - started) * 1000)
            calls_per_analysis.append(_BenchProvider.calls)
    finally:
        analyzer.get_provider = original_get_provider  # type: ignore[assignment]
        if hasattr(analyzer, "_reset_provider_cache"):
            analyzer._reset_provider_cache()

    return {
        "delay_s": delay,
        "iterations": iterations,
        "analyze_ms_mean": round(statistics.mean(durations), 2),
        "analyze_ms_p50": round(_pctl(durations, 50), 2),
        "analyze_ms_p95": round(_pctl(durations, 95), 2),
        "analyze_ms_min": round(min(durations), 2),
        "analyze_ms_max": round(max(durations), 2),
        "provider_calls_per_analysis": statistics.mode(calls_per_analysis),
        "max_concurrent_provider_calls": _BenchProvider.max_concurrent,
    }


def measure_frame_extraction(clip_path: Path) -> dict:
    """Cold vs warm frame extraction (warm should hit the frame cache, if present)."""
    import services.ai_analyzer as analyzer

    clip_id = "benchframes"
    # Cold: clear any prior frames for this id.
    frame_dir = analyzer.FRAME_DIR / clip_id
    if frame_dir.exists():
        for f in frame_dir.glob("*.jpg"):
            f.unlink()
    t0 = perf_counter()
    cold = analyzer._extract_frames(str(clip_path), clip_id)
    cold_ms = (perf_counter() - t0) * 1000
    t1 = perf_counter()
    warm = analyzer._extract_frames(str(clip_path), clip_id)
    warm_ms = (perf_counter() - t1) * 1000
    return {
        "frames_extracted": len(cold),
        "cold_ms": round(cold_ms, 2),
        "warm_ms": round(warm_ms, 2),
        "warm_reused_cache": len(warm) == len(cold) and warm_ms < cold_ms * 0.5,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sprint 6 offline performance benchmark.")
    parser.add_argument("--clip", default="/tmp/refcheck_bench/bench_clip.mp4")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--output", default=None, help="Write the results JSON here.")
    args = parser.parse_args(argv)

    clip_path = Path(args.clip)
    if not clip_path.exists():
        parser.error(f"Benchmark clip not found: {clip_path}. Generate one with ffmpeg (see docstring).")

    results = {
        "frame_extraction": measure_frame_extraction(clip_path),
        "orchestration_overhead": run_benchmark(clip_path, args.iterations, delay=0.0),
        "network_bound": run_benchmark(clip_path, args.iterations, delay=0.5),
    }
    text = json.dumps(results, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text)
        print(f"\nWritten to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
