# Backend Performance Optimization (Sprint 6)

This document records every optimization applied to the multi-agent analysis
pipeline in Sprint 6, the before/after benchmark numbers, and how to reproduce
them. (The pipeline was 4 agents at the time of Sprint 6; Sprint 16A later removed
the Retrieval agent, so it is now 3 — see the notes below.) **The public API contract is unchanged** — every optimization is either a
transparent internal change or opt-in behind an environment flag (default OFF).

## How to reproduce the benchmark

The pipeline's latency is dominated by model round-trips, which need network + an
API key. To measure the optimizations **offline and deterministically**,
`scripts/perf_benchmark.py` exercises the real `analyze_clip` orchestration with a
simulated-latency provider (no network, no key):

```bash
# from backend/, with the venv active
# one-time: a real (non-placeholder) clip so frame extraction actually runs
ffmpeg -y -f lavfi -i testsrc=duration=4:size=640x480:rate=15 -pix_fmt yuv420p \
    /tmp/refcheck_bench/bench_clip.mp4

python scripts/perf_benchmark.py --iterations 6 --output after.json
```

- `--delay 0` isolates **pure-Python orchestration overhead** (frame extraction,
  rule-record rebuilds, JSON serialization, provider instantiation).
- `--delay 0.5` simulates **network-bound model calls**, so the effect of running
  the two adjudicators concurrently is visible.

The harness also counts `send_messages` calls per analysis (the "duplicate
requests" signal) and the max number of concurrent provider calls.

## Results: before → after

Measured on the same machine, 6 iterations, synthetic 4 s clip.

| Metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| Warm frame extraction (re-analysis) | 101.82 ms | **0.14 ms** | −99.9% (~727×) |
| Orchestration overhead (`delay=0`, mean) | 105.59 ms | **1.84 ms** | −98.3% (~57×) |
| Network-bound analysis (`delay=0.5`, mean) | 2144.59 ms | **1516.97 ms** | −29.3% (−628 ms) |
| Max concurrent provider calls | 1 | **2** | adjudicators overlap |
| Repeat identical analysis, `ANALYSIS_CACHE=1` | 4 Claude calls | **0 Claude calls** | −100% |

The network-bound figure is the real-world win: the four model calls are
`perception → retrieval → {adjudicator A ∥ adjudicator B}`. Serializing the two
independent adjudicators cost ~2× a round-trip; running them concurrently costs
~1×, cutting a full analysis from ~4 to ~3 round-trips.

## Profiling: where the time actually went

The baseline benchmark localized the two bottlenecks precisely:

1. **Frame extraction ran on every call.** `_extract_frames` re-invoked `ffprobe`
   **and** `ffmpeg` for a clip whose frames were already on disk — ~100 ms of
   subprocess overhead per analysis, dominating the 105 ms orchestration cost.
2. **All four model calls were serialized** (`max_concurrent = 1`), even the two
   adjudicators that share no state.

Everything below targets one of those, plus lower-cost cleanups (rule-record
rebuilds, provider churn, duplicate prompt serialization) that the `delay=0`
profile surfaced.

## The optimizations

All pipeline changes are in `services/ai_analyzer.py` unless noted.

### 1. Concurrent adjudicators (latency)
`_run_four_agent_pipeline` now submits adjudicator A (conservative, temp 0.2) and
adjudicator B (skeptical, temp 0.7) to a 2-worker `ThreadPoolExecutor` instead of
calling them one after the other. The providers do blocking socket I/O, which
releases the GIL, so the two calls overlap in wall-clock time. A failure in either
thread re-raises through `future.result()` and is caught by the existing
`except`, so the mock-fallback behavior on error is byte-for-byte unchanged.
**Effect:** −628 ms per network-bound analysis; `max_concurrent` 1 → 2.

### 2. Frame-extraction cache (latency + subprocess load)
`_extract_frames` returns frames already on disk for a `clip_id` before running
`ffprobe`/`ffmpeg`. `clip_id` is a hash of the stored path + byte size, so cached
frames are byte-for-byte the correct frames for that clip. Re-analysis (demo
suite, benchmark loops, a user resubmitting) skips both subprocesses.
**Effect:** warm extraction 101.82 ms → 0.14 ms.

### 3. Build the adjudicator prompt once (CPU + memory)
Both adjudicators receive an **identical** user prompt — only the system framing
and temperature differ. The prompt (perception JSON + retrieved rules + sport
signals + tracked evidence) was serialized twice per analysis. It is now built
once in `_build_adjudicator_prompt` and passed to both. Halves the transient
string allocation for the largest payload in the pipeline; the prompt text is
identical to before.

### 4. Rule-record cache (CPU)
`_rule_records(sport)` is now `@lru_cache`-d and returns an immutable tuple. The
static rulebook was rebuilt — and `rules.sport_config` re-imported — on every
retrieval (once per analysis). Now built once per sport per process.

### 5. Rule-ranking memoization (CPU) — _superseded by Sprint 16A_
Sprint 6 memoized the keyword rule ranker (`_rank_rules`/`_retrieve_rules`) with
`@lru_cache`. **Sprint 16A removed the retrieval/ranking stage entirely** — the full
rule corpus is injected into the adjudicators — so there is nothing left to rank or
memoize here. The corpus load itself is still cached (see §4, `_rule_records`).

### 6. Provider-instance cache (memory + CPU)
`get_provider()` re-read `AI_PROVIDER` and instantiated a fresh provider object
on each of the ~5 calls per analysis. `_active_provider()` caches the instance
keyed on the resolved provider name; a changed `AI_PROVIDER` (e.g. the evaluation
CLI swapping providers) produces a new key and still re-resolves. Providers read
their secrets/model lazily inside `send_messages`, so a cached instance never goes
stale. `_reset_provider_cache()` exists for tests/benchmarks.

### 7. Async route offload (concurrency, `main.py`)
`analyze_clip` is a blocking multi-second pipeline that was being called directly
inside the `async` FastAPI handlers, stalling the event loop for the whole
analysis. Both `/analyze` and `/api/analyze` now `await asyncio.to_thread(...)`,
so the event loop stays free to serve other requests. The response is identical.

### 8. Opt-in analysis result cache — "reduce duplicate Claude requests"
Within a single analysis the agents are all distinct calls; there are **no
duplicate model requests to remove**. Duplicate requests arise *across* analyses
of the same clip (demo suites, evaluation benchmarks re-running a dataset, a user
resubmitting). When `ANALYSIS_CACHE` is truthy (`1`/`true`/`yes`/`on`), the fully
built response is memoized by `(clip_id, sport, level, league, original_call,
referee, provider, model)`; a repeat analysis returns a deep copy instantly with
**zero** model calls.

**Default is OFF**, so the public API is byte-for-byte identical to today. It is
opt-in because adjudicator B runs at temperature 0.7 — re-running the same clip is
intentionally non-deterministic unless caching is explicitly enabled.
**Effect (enabled):** repeat identical analysis 4 → 0 Claude calls.

## A note on "cache embeddings"

The Sprint 6 brief asked to *cache embeddings*. There were never any embeddings or
FAISS index in this pipeline (the FAISS/`sentence-transformers` description in older
docs describes an architecture this backend never shipped) — and as of Sprint 16A
there is no retrieval stage at all: the full rule corpus is injected into the
adjudicators. The equivalent caching win therefore lives in the static rule-corpus
load (#4, `_rule_records`), plus the opt-in whole-result cache (#8). If an
embedding-based retriever is added later, its embeddings should be cached by content
hash following the same pattern.

## What was intentionally *not* changed

- **Frame content** (count, resolution, spacing) is untouched — changing it would
  change perception output and therefore verdicts.
- **Prompt text, temperatures, model, reconciliation logic** are unchanged.
- **Response schema** (`schemas.py` / `frontend/src/lib/types.ts`) is unchanged —
  no frontend update required.
