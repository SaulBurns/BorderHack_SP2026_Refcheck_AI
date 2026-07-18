"""HTTP middleware overhead benchmark (Sprint 15 — production readiness).

The Sprint 15 production layer adds an observability middleware (request-id,
structured logging, metrics) + optional auth/rate-limit checks to every request.
This measures the per-request overhead that layer adds, by timing a health check
against (a) a bare FastAPI app with no middleware ("before") and (b) the real
production app ("after"), so the "before and after" delta is explicit.

Run from backend/:
    python scripts/prod_overhead_benchmark.py --iterations 2000

Offline and deterministic — hits `/api/health` only (no pipeline, no network).
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from time import perf_counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _bare_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/health")
    def health():  # noqa: ANN202 - benchmark stub
        return {"status": "ok", "message": "RefCheck AI backend is running"}

    return app


def _time_requests(client: TestClient, iterations: int) -> list[float]:
    # Warm up (route resolution, first-call import costs).
    for _ in range(50):
        client.get("/api/health")
    samples: list[float] = []
    for _ in range(iterations):
        start = perf_counter()
        client.get("/api/health")
        samples.append((perf_counter() - start) * 1000.0)  # ms
    return samples


def _summary(name: str, samples: list[float]) -> dict:
    ordered = sorted(samples)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    return {
        "name": name,
        "mean_ms": round(statistics.mean(samples), 4),
        "p50_ms": round(statistics.median(samples), 4),
        "p95_ms": round(p95, 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=2000)
    args = parser.parse_args()

    before = _summary("before (bare app)", _time_requests(TestClient(_bare_app()), args.iterations))

    # Import the real app lazily so the bare baseline is unpolluted.
    import main  # noqa: E402

    after = _summary("after (production app)", _time_requests(TestClient(main.app), args.iterations))

    overhead = round(after["mean_ms"] - before["mean_ms"], 4)
    print(f"iterations: {args.iterations}")
    for row in (before, after):
        print(f"  {row['name']:>26} | mean {row['mean_ms']:.4f} ms | "
              f"p50 {row['p50_ms']:.4f} ms | p95 {row['p95_ms']:.4f} ms")
    print(f"  middleware overhead per request: {overhead:.4f} ms "
          f"({overhead * 1000:.1f} µs)")


if __name__ == "__main__":
    main()
