# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (run from `backend/`)

```bash
# First-time setup
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Start production backend (real pipeline). AI_PROVIDER=mock runs offline.
ANTHROPIC_API_KEY=sk-ant-... AI_PROVIDER=anthropic CORS_ORIGINS=http://localhost:3000 \
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
source venv/bin/activate
pytest tests/

# Run a single test
pytest tests/test_sport_routing.py::test_rule_records_basketball_returns_nine_rules -v

# Syntax/import check (no venv needed for this quick check)
python3 -m compileall services/ main.py

# Performance benchmark (offline; Sprint 6). Exercises the real analyze_clip
# orchestration with a simulated-latency provider — no network/key needed.
# One-time: create a real clip so frame extraction runs:
#   ffmpeg -y -f lavfi -i testsrc=duration=4:size=640x480:rate=15 \
#     -pix_fmt yuv420p /tmp/refcheck_bench/bench_clip.mp4
python scripts/perf_benchmark.py --iterations 6 --output after.json
```

### Frontend (run from `frontend/`)

```bash
npm install
npm run dev          # http://localhost:3000
npm run build        # production build check
```

### Local env file

`frontend/.env.local` must contain:
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Architecture

This is a multi-agent AI pipeline for reviewing sports officiating calls. A user uploads a video clip; the backend runs a 4-agent pipeline and returns a structured verdict; the frontend displays it.

> Note: there is **no `backend/app/` package** and **no FAISS/`sentence-transformers`**. Earlier
> revisions of this doc described an aspirational `app/agents/…` + FAISS design that this backend
> never shipped. The real code lives under `backend/services/` and retrieval is keyword-based.

### Agent pipeline (`backend/services/`)

The pipeline is orchestrated by `services/ai_analyzer.py:analyze_clip()` — a **synchronous** function the FastAPI routes call via `asyncio.to_thread` (Sprint 6). It talks to LLMs only through the provider seam (`_send_messages` → `services/ai/`), so it runs against Anthropic, Gemini, or the offline mock unchanged.

```
analyze_clip(file, sport, ..., video_metadata)      services/ai_analyzer.py
  │
  ├─ _extract_frames()          services/analysis/frames.py
  │    ffprobe duration + ffmpeg → 10 evenly-spaced JPEGs (clip_id-cached on disk)
  │
  └─ _run_four_agent_pipeline()                       services/ai_analyzer.py
       ├─ detector.detect()     services/detectors/  (default claude_vision → _perception_agent)
       │    Claude vision over the frames → perception dict (no verdict)
       ├─ _retrieval_agent()    Claude turns perception into a rulebook query
       ├─ _retrieve_rules()     services/analysis/retrieval.py
       │    keyword scoring over rules.sport_config (NO embeddings/FAISS) → top 5
       ├─ adjudicators A ∥ B    conservative (temp 0.2) ∥ skeptical (temp 0.7),
       │    run concurrently on a ThreadPoolExecutor; identical prompt built once
       └─ (mock/degraded runs return services/analysis/mock_result.py)
  │
  └─ _build_response() → _reconcile()                 services/ai_analyzer.py
       agree → that verdict, averaged confidence (± tracking nudge)
       disagree / weak perception → inconclusive, damped confidence
```

### Sport plugins (`backend/sports/`) — self-contained sport architecture

Sports are **fully self-contained plugins**. Each sport implements the `Sport` interface and is registered in a `SportRegistry`; every generic seam resolves a plugin with `get_sport(sport)` and delegates, so **no shared file hardcodes a sport name** — `ai_analyzer.py`, the providers, detectors, evaluation, diagnostics, reconciliation, and frontend API are all sport-agnostic.

```
sports/
  base.py         # Sport ABC — the full contract each plugin implements:
                  #   display_name, perception/retrieval/adjudicator prompts,
                  #   rule_records, boost_rule_score, detail_extractor, details_model,
                  #   sport_details, tracked_evidence, metadata_provider
  registry.py     # SportRegistry + get_sport() (GenericSport fallback for unregistered sports)
  generic.py      # GenericSport — empty/stub defaults for any UNREGISTERED sport string
  basketball/  soccer/  hockey/  lacrosse/     # four full implementations, identical layout:
    sport.py         # <Sport>Sport wiring (implements the whole Sport interface)
    prompts.py       # perception/retrieval/adjudicator prompt strings (incl. basketball)
    rules.py         # rule-retrieval boosts (corpus in rules/<sport>_rules.py)
    tracking.py      # tracked-evidence layer (soccer/hockey/lacrosse; basketball uses basketball_vision)
    extractor.py     # <Sport>DetailExtractor -> <Sport>Details (basketball's is services/extractors/basketball.py)
    game_context.py  # metadata-provider seam (basketball -> NBA provider; others None)
```

- **What the plugin owns (the whole `Sport` contract):** `display_name`, the three prompts, `rule_records()` (the corpus), `boost_rule_score()`, `detail_extractor()`, `details_model()` (the `SportDetails` subclass), `sport_details()`, `tracked_evidence()`, and `metadata_provider()`. Basketball is symmetric with the others (its prompts live in `sports/basketball/prompts.py`).
- **How the generic seams delegate (no hardcoded per-sport tables):** every shared lookup resolves `get_sport(sport)` and calls the matching method —
  - `rules/sport_config.py:get_rules_for_sport()` → `.rule_records()`; `normalize_sport()`/`supported_sports()` → `registry.available()`
  - `services/analysis/prompts.py:_get_*_prompt()` → `.perception_prompt()`/`.retrieval_prompt()`/`.adjudicator_prompt()`
  - `services/analysis/retrieval.py` → `.boost_rule_score()`
  - `services/extractors/registry.py:get_extractor()` → `.detail_extractor()`
  - `services/perception_schema.py:get_sport_details_model()` → `.details_model()`
  - `services/metadata/registry.py:get_metadata_provider()` → `.metadata_provider()`
  - `ai_analyzer._run_four_agent_pipeline` → `.sport_details()` and `.tracked_evidence()`

  These generic functions stay as the stable, monkeypatchable seams; only the *decision* lives in the plugin. Import cycles are avoided by lazy `from sports import get_sport` inside the delegating functions, and by keeping all `services`/`rules` imports lazy (inside methods) in every `sports/<sport>/sport.py`.
- **Unregistered sports** resolve to a name-carrying `GenericSport`: empty rules, stub prompts, `EmptyDetailExtractor`, `EmptySportDetails`, no tracking, no game context — the graceful Claude-only fallback, never a crash.
- **Supported events:** **soccer** — foul, offside, handball, penalty, red card, yellow card, goal; **hockey** — icing, offside, tripping, cross-checking, boarding, slashing, hooking; **lacrosse** — illegal body check, slash, push, crease violation, offside, loose-ball push. Each is a rule record in `rules/<sport>_rules.py` (keys become uppercase `rule_id`s) returned by the plugin's `rule_records()`, with a tuned boost in `sports/<sport>/rules.py`.
- **Adding a sport = exactly three steps, no other backend file changes:**
  1. Create `sports/<sport>/` implementing the `Sport` interface (prompts, `rule_records`, boosts, `detail_extractor`, `details_model`, tracking, game context).
  2. (Its rule corpus + `SportDetails` subclass can live inside the package — a new sport touches neither `rules/sport_config.py` nor `services/perception_schema.py`.)
  3. `registry.register(<Sport>Sport())` in `sports/registry.py`.

  The pipeline, providers, detectors, evaluation, diagnostics, reconciliation, and frontend API need zero changes. This is proven by `tests/test_sport_self_contained.py`, which registers a brand-new sport entirely inline and asserts every seam routes through it.

### The `services/analysis/` package (Sprint 7)

`ai_analyzer.py` was ~1500 lines; its concerns were split into a package, leaving `ai_analyzer` as the orchestrator (~700 lines). Every name is re-imported into `ai_analyzer`, so `from services.ai_analyzer import ...` and `monkeypatch.setattr(ai, ...)` seams are unchanged.

- `prompts.py` — shared reasoning framings, generic stub-prompt builders, and the `_get_*_prompt(sport)` selectors that now **delegate to `get_sport(sport).*_prompt()`** (each sport's prompt strings live in `sports/<sport>/prompts.py`).
- `frames.py` — `FRAME_DIR`, ffprobe/ffmpeg frame extraction + on-disk cache.
- `retrieval.py` — keyword rule-record loading + ranking (both `@lru_cache`d).
- `mock_result.py` — the canned, network-free demo result.
- `diagnostics.py` — additive detection/YOLO-influence diagnostics.
- `contracts.py` — `TypedDict`s (`RuleRecord`, `AdjudicatorOutput`, `AgentResult`) documenting the payload shapes (annotation-only; no runtime validation).

`ai_analyzer.py` still owns orchestration, the provider-instance + result caches, reconciliation, and response building.

### Response shape / frontend contract

The response is assembled as plain dicts in `_build_response` / `_frontend_perception` (there is no `schemas.py`). `frontend/src/lib/types.ts` mirrors that shape — **keep the two in sync**. `services/perception_schema.py` holds the Pydantic `SportDetails` models (live) and a reserved sport-neutral `PerceptionCore` (not yet wired).

### FastAPI entrypoint (`backend/main.py`)

- `GET /api/health` — Render healthcheck; `GET /` — liveness.
- `POST /api/analyze` — multipart (`file`, `sport`, `level`, `league`, `original_call`, `ref_name`); saves the clip, runs `analyze_clip` off the event loop, persists via `services/supabase_store.py`. `POST /analyze` is the same with legacy field names.
- `GET /api/clips/{name}`, `GET /api/frames/{clip_id}/{name}`, `GET /api/feed` — media + feed.
- CORS origins come from `FRONTEND_ORIGIN` / `CORS_ORIGINS` (comma-separated) plus a `*.vercel.app` regex.

Deploy: Docker (`backend/Dockerfile`) → `uvicorn main:app`. There is no `build.sh`.

### AI provider abstraction

The four-agent pipeline talks to LLMs **only** through the provider interface in `backend/services/ai/`. The rest of the app never knows whether it is speaking to Anthropic, Gemini, or the mock.

**Where providers live:**

```
backend/services/ai/
  provider.py                  # AIProvider ABC + neutral message content (text/image parts)
  factory.py                   # get_provider() — selects by AI_PROVIDER, raises on invalid
  providers/
    anthropic_provider.py      # Claude Messages API (HTTP)
    gemini_provider.py         # Google GenAI SDK (google-genai, lazy-imported)
    mock_provider.py           # demo-safe, no network
```

**The interface** (`AIProvider`): `send_messages(system_prompt, user_content, temperature, max_tokens) -> str`, `supports_vision()`, `provider_name()`, and an `is_mock` property.

**How the pipeline interacts with providers:** `ai_analyzer.py` resolves the active provider once via `get_provider()` (from `AI_PROVIDER`). If `provider.is_mock`, it takes the canned demo path (`_mock_ai_result`, unchanged output). Otherwise the three real agents (`_perception_agent`, `_retrieval_agent`, `_adjudicator_agent`) send their turns through the single `_send_messages()` seam, which delegates to `provider.send_messages()`. Message content is provider-neutral: callers pass a string or a list of `text_part(...)` / `image_part(path)` parts, and each provider translates them into its own wire format. The raw text reply is parsed by the **shared** `_extract_json()` in `ai_analyzer.py` — parsing is never duplicated per provider.

**Why provider-specific logic must never leak into `ai_analyzer.py`:** the analyzer owns the *pipeline* (agents, reconciliation, diagnostics), not vendor plumbing. Keeping HTTP/SDK/auth/model-name/image-encoding details inside the provider classes is what makes providers swappable by env var alone and keeps the pipeline untouched when a backend changes.

**Environment configuration:** `AI_PROVIDER` selects the provider (`mock` | `anthropic` | `gemini`; default `mock`; invalid values raise a clear error). `anthropic` needs `ANTHROPIC_API_KEY` (model override: `AI_MODEL`, default `claude-sonnet-4-5`). `gemini` needs `GEMINI_API_KEY` and the `google-genai` package (model override: `GEMINI_MODEL`, default `gemini-2.5-flash`). Missing keys degrade to the mock fallback with the reason surfaced in diagnostics; an unsupported `AI_PROVIDER` value fails loudly.

**Adding a future provider** (OpenAI, Azure, Grok, Ollama, …): (1) create one class implementing `AIProvider` under `providers/`, (2) add one `_registry.register(...)` line in `factory.py` (the shared `services/registry.Registry`). The four-agent pipeline requires zero changes. Design principle for contributors: a provider only knows how to turn a system prompt + neutral content + temperature/max_tokens into a text reply — it must not import `ai_analyzer`, know about agents, or reshape JSON.

### Hybrid perception grounding (YOLO tracked evidence)

**Principle:** YOLO tracked detections are *supporting evidence only*. Claude Vision remains the semantic authority; detections ground the adjudicators' reasoning but never replace it, and never change the frontend API contract.

**Detector paths** (`DETECTOR` env): `claude_vision` (semantic only, `detections=None`), `yolov8` (detections only), `hybrid` (Claude perception + YOLO detections). `hybrid` degrades gracefully: if YOLO inference fails (e.g. ultralytics missing, bad frame), `HybridDetector.detect` keeps Claude's perception and drops tracking (`detections=None`) instead of failing the analysis — the four-agent pipeline still runs, and diagnostics show `detections_present=False`.

**How detections influence the verdict** (all in `_run_four_agent_pipeline` / `_build_response`, basketball-scoped):
- `services/extractors/basketball_vision.py:summarize_tracked_evidence()` turns `RawDetections` into a compact evidence dict: offensive/defender `track_id`s, per-frame `possession_timeline`, `possession_changes`, ball-handler + defender movement, **ball's own `ball_movement`** (from `track_ball`, independent of any player), and a `tracking_confidence ∈ [0,1]`.
- This evidence is attached to **both** adjudicator prompts (`_adjudicator_agent`, `TRACKED DETECTION EVIDENCE` section) alongside `sport_details` — computed once, passed to both.
- `_reconcile` takes the evidence's `tracking_confidence` and applies a bounded ±0.05 nudge to the final confidence **only when the adjudicators agree** (calibrate, never decide).
- `_frontend_perception` maps detection-derived signals into `sport_details` (the frontend block) — enrichment only; every legacy field is preserved.

**Single-scan dedup:** the controlling player per frame is computed exactly once via `_scan_controllers`; `possession_status`, `identify_primary_defender`, `analyze_basketball`, and `summarize_tracked_evidence` all derive from that shared scan instead of re-scanning the frames.

**Influence diagnostics:** `_diagnostics_payload` reuses the already-computed `tracked_evidence` (no recomputation) to expose `yolo_influenced`, `tracked_evidence_present`, `tracking_confidence`, `possession_summary`, `defender_tracked`, `ball_trajectory_present`, and `influenced_reconciliation` — so it is visible when and how YOLO shaped a decision.

**Scope note:** basketball, soccer, hockey, and lacrosse each own a tracked-evidence layer (`services/extractors/basketball_vision.py`, `sports/soccer/tracking.py`, `sports/hockey/tracking.py`, `sports/lacrosse/tracking.py`), reached via `get_sport(sport).tracked_evidence(detections)`; an unregistered sport (GenericSport) returns `None` and gets Claude-only perception, unchanged. The soccer/hockey/lacrosse tracking layers reuse the sport-agnostic primitives (`track_players`, `trajectory_movement`) from `basketball_vision` and add sport-specific ball/puck-label handling + possession/direction framing.

### Demo suite & curated dataset

`backend/demo_clips/manifest.json` is a curated basketball dataset: 10 officiating scenarios (charge, blocking foul, shooting foul, travel, double dribble, out of bounds, goaltending, illegal screen, verticality, loose-ball foul). Each entry carries `scenario`, `original_call`, metadata (`game_date`/`home_team`/`away_team`), an `expected_verdict`, an `expected_rule_id` (a `rules/basketball_rules.py` key, or `null` when no rule chunk backs that scenario yet), a human-readable `rule_citation`, an `expected_confidence` (`high`/`medium`/`low`), and `notes`. Only `clip_id`/`sport`/`video_path`/`original_call` are required — every added field is optional and backward compatible.

`backend/scripts/run_demo_suite.py` runs the suite. Sponsors run it with zero arguments (`python scripts/run_demo_suite.py`) — `--manifest` defaults to `DEFAULT_MANIFEST` (the shipped manifest). It runs each clip through the **real** `analyze_clip` (reusing `demo_analyze.run_demo` / `_real_pipeline_ran` — one source of truth for "did the real pipeline run?"), and writes `demo_reports/demo_report.{md,json}` (gitignored). The Markdown report has an aggregate-metrics table (verdict accuracy, rule-citation accuracy, confidence-expectation rate, scenario coverage, verdict distribution, average confidence), a results-at-a-glance table, and per-clip detail. `--strict-real`, `--clip-id`, `--limit`, `--provider`, `--detector` all work as before.

`backend/demo_clips/soccer_manifest.json` (Sprint 10), `backend/demo_clips/hockey_manifest.json` (Sprint 11), and `backend/demo_clips/lacrosse_manifest.json` (Sprint 12) are the matching curated **soccer**, **hockey**, and **lacrosse** datasets (soccer: foul, offside, handball, penalty, red card, yellow card, goal — 7; hockey: icing, offside, tripping, cross-checking, boarding, slashing, hooking — 7; lacrosse: illegal body check, slash, push, crease violation, offside, loose-ball push — 6), same schema, `expected_rule_id`s keyed to `rules/<sport>_rules.py`. Run with `python scripts/run_demo_suite.py --manifest demo_clips/<sport>_manifest.json`.

The checked-in `demo_clips/*.mp4` are **placeholders** (a valid MP4 header, no footage) so the suite runs anywhere; real footage is dropped at those paths for a live demo. Adding a scenario = one manifest entry (+ a clip file); the runner and report pick it up automatically.

### Evaluation & benchmarking framework (`backend/evaluation/`)

A standalone, offline-friendly harness that benchmarks verdict accuracy and compares providers. It is pure Python (no heavy pipeline import unless it actually drives `analyze_clip`), so metrics/report tests run fast.

```
backend/evaluation/
  models.py     # LabeledClip / Prediction / EvaluationRecord, prediction_from_response
  metrics.py    # accuracy, per_class (precision/recall/F1), macro/micro averages,
                # confusion_matrix, cohens_kappa, reliability_bins, expected_calibration_error (ECE)
  latency.py    # LatencySummary + summarize_latencies (mean/p50/p95/min/max)
  runner.py     # EvaluationReport (from records) + evaluate()/evaluate_predictions()
  cli.py        # collect_predictions() drives the pipeline for one provider (shared seam),
                # run_evaluation(), and `python -m evaluation` main()
  benchmark.py  # run_benchmark(dataset, providers, detector) -> BenchmarkReport (per-provider
                # EvaluationReport + LatencySummary) for side-by-side comparison
  report.py     # render_markdown() / render_html() — provider comparison table, confusion
                # matrices, per-class tables, calibration bins, latency
```

**Datasets**: a JSON array of rows with `clip_id`, `sport`, `ground_truth_verdict` (required) and optional `video_path` / `original_call` (used to drive the pipeline). `data/eval/labeled_clips.example.json` is a 3-clip smoke set; `data/eval/benchmark_basketball.json` is the 10-scenario basketball benchmark, `data/eval/benchmark_soccer.json` (Sprint 10) the 7-scenario soccer benchmark, `data/eval/benchmark_hockey.json` (Sprint 11) the 7-scenario hockey benchmark, and `data/eval/benchmark_lacrosse.json` (Sprint 12) the 6-scenario lacrosse benchmark, all derived from the demo datasets.

**Metrics**: overall accuracy, per-class + macro + micro precision/recall/F1, confusion matrix, Cohen's kappa, confidence calibration (reliability bins + ECE), and inference latency (mean/p50/p95). **Provider comparison** runs the same dataset through `mock` | `anthropic` | `gemini` and tabulates the differences.

**CLI** (`python -m evaluation`):
```bash
# Single provider -> EvaluationReport JSON (Phase 9 schema, backward compatible):
python -m evaluation --dataset data/eval/benchmark_basketball.json --provider mock --output report.json
# Provider comparison -> BenchmarkReport JSON + Markdown + HTML:
python -m evaluation --dataset data/eval/benchmark_basketball.json \
    --providers mock,anthropic,gemini --output bench.json --md bench.md --html bench.html
```
Both modes flow through `run_benchmark`; single-provider still writes the bare `EvaluationReport` JSON. The pipeline is reached only through `cli.collect_predictions` (the same provider/env seam as everything else), and tests inject `analyze_fn` to run offline. Real providers without keys degrade to the mock fallback (surfaced in the run), so the benchmark always produces a report.

### Frontend (`frontend/`)

Next.js 15 App Router. Six screens in `src/app/screens/` — `Home`, `Upload`, `Verdict`, `Feed`, `Leaderboard`, `RefProfile` — each has a thin page wrapper in `src/app/<route>/page.tsx`.

The only file that talks to the backend is `src/lib/api.ts`. It reads `NEXT_PUBLIC_API_BASE` (must be set at **build time** for Vercel, not just runtime). `analyzeClip()` POSTs multipart form data; the verdict is cached in `sessionStorage` keyed by `clip_id` so the verdict page survives a reload without re-calling the API.

#### Sport-agnostic UI (Sprint 13)

**The frontend never assumes basketball.** Every rendering path is sport-aware, mirroring the backend's self-contained Sport plugins — a new backend sport renders with no frontend change.

- **UI sport registry (`src/lib/sports.ts`)** is the single source of truth: each of the four sports has full support (no more "preview" concept) plus an `overlay` vocabulary (`offense`/`defense`/`object` labels, e.g. hockey → "Puck carrier"/"Puck"). `overlayVocab(sport)` returns a neutral default for any unknown sport.
- **Dynamic `sport_details` rendering (`src/lib/sportDetails.ts`).** `dynamicSportDetailRows(sport, perception)` walks whatever fields `perception.sport_details[sport]` contains (booleans → yes/no, strings → humanized, nested blocks flattened) and returns labeled rows — so a brand-new sport's signals render field-by-field with no bespoke code. `diagnosticRows(diagnostics)` renders the tracked-evidence/pipeline diagnostics the same way. Both are pure and unit-tested (`sportDetails.test.ts`). `SportDetailsMap` in `types.ts` has an index signature so a sport block can be read dynamically by name.
- **Verdict screen** shows sport-agnostic panels: the verdict banner + **confidence**, the **Ref Review Checklist** (neutral rows + sport-aware rows from `sportEvidence.ts`), a **`<Sport>` Signals** panel (`dynamicSportDetailRows`), an **Analysis Diagnostics** panel (`diagnosticRows`, i.e. tracked evidence), the **rulebook citation** block (reads `verdict.cited_rule` generically), and the game-context block (label derived from `game_context.provider`, not hardcoded "NBA").

#### AI reasoning overlay (Verdict screen)

The Verdict screen renders a **sport-aware AI Reasoning Overlay** on the uploaded clip via `src/app/components/AiReasoningPanel.tsx`. It layers: tracked players, the tracked ball/puck, the impact zone, movement arrows, a confidence heatmap, a possession timeline, an event timeline, and key-frame navigation. Layers are individually toggleable. Marker labels and the object label come from the sport's `overlayVocab`; possession is read from the sport-agnostic `diagnostics.possession_summary` (with the basketball `offensive_control_status` as a graceful fallback, read by sport key — never assuming basketball).

- **No backend API change.** The overlay is built entirely from data the `/api/analyze` response already returns: `verdict.perception` (impact zone, `players_involved`, `frame_observations`, `sport_details`), `verdict.confidence`, `key_moment`, and the `diagnostics` block, mirrored in `src/lib/types.ts` (`Diagnostics`).
- **Pure geometry is isolated and unit-tested.** `src/lib/overlay.ts` holds the framework-free helpers (`buildOverlayMarkers(perception, impact, sport)`, `movementVector` — sport-neutral labels, `buildEventTimeline`, `buildKeyFrames`, `possessionSegments`), covered by `src/lib/overlay.test.ts`.
- **Honest positioning.** The backend does not expose raw per-frame CV bounding boxes, so player/ball markers use an AI-reasoning layout anchored on the real impact zone and driven by the detected roles/possession/movement — labeled as approximate in the UI. Everything else (impact zone, confidence, possession, timelines) is real response data.
- **Rendering components:** `ReasoningOverlay.tsx` (SVG/CSS layers over the video), `ReasoningTimelines.tsx` (`PossessionTimeline` / `EventTimeline` / `KeyFrameNav`), composed by `AiReasoningPanel.tsx`, which owns the `<video>` ref so timeline/key-frame clicks seek playback.

Run `npm run build` (or `npm test` for the pure units: `overlay`, `sportEvidence`, `sportDetails`) after touching these.

### Performance optimizations (Sprint 6)

The four-agent pipeline was profiled and optimized for latency, redundant model
calls, and memory. **The API contract is unchanged**: every optimization is a
transparent internal change or opt-in behind an env flag (default OFF). Full
write-up with before/after numbers: `backend/PERFORMANCE.md`. Benchmark harness:
`backend/scripts/perf_benchmark.py` (offline; simulated-latency provider).

Headline results (offline benchmark, 6 iterations): warm frame extraction
101.8 ms → 0.14 ms; orchestration overhead 105.6 ms → 1.8 ms; network-bound
analysis 2144 ms → 1517 ms (−29%); repeat identical analysis (with
`ANALYSIS_CACHE=1`) 4 → 0 Claude calls.

What changed (all in `services/ai_analyzer.py` unless noted):
- **Concurrent adjudicators.** A (conservative) and B (skeptical) are independent
  model calls; they now run on a 2-worker `ThreadPoolExecutor` (provider socket
  I/O releases the GIL, so they overlap). Errors re-raise via `future.result()`
  into the existing `except`, preserving the exact mock-fallback behavior.
- **Frame-extraction cache.** `_extract_frames` reuses frames already on disk for
  a `clip_id` (a hash of stored path + byte size), skipping `ffprobe`+`ffmpeg` on
  re-analysis. Frame content is byte-for-byte identical.
- **Adjudicator prompt built once.** Both adjudicators receive an identical user
  prompt (only system framing/temperature differ); `_build_adjudicator_prompt`
  builds it once instead of serializing the perception+rules payload twice.
- **Rule caches.** `_rule_records(sport)` is `@lru_cache`-d (immutable tuple) and
  `_rank_rules(haystack, sport, limit)` memoizes the pure ranking step;
  `_retrieve_rules` still returns a fresh `list`.
- **Provider-instance cache.** `_active_provider()` caches the resolved provider
  keyed on the `AI_PROVIDER` value (re-resolves on change); `get_provider()`
  stays the pure factory seam. `_reset_provider_cache()` for tests/benchmarks.
- **Async route offload (`main.py`).** `/analyze` and `/api/analyze` call the
  blocking pipeline via `await asyncio.to_thread(...)` so it no longer stalls the
  event loop. Identical response.
- **Opt-in result cache.** `ANALYSIS_CACHE` (truthy = on; default OFF) memoizes
  the full response by `(clip_id, sport, level, league, original_call, referee,
  provider, model)`, so a repeat analysis returns a deep copy with zero model
  calls. Off by default because adjudicator B is temperature 0.7 (re-running is
  intentionally non-deterministic unless caching is enabled).

Note: there are **no embeddings/FAISS** in this pipeline — retrieval is
keyword-based — so "cache embeddings" maps to the rule-corpus/ranking caches
above (see `backend/PERFORMANCE.md`).

### Configuration & shared utilities (Sprint 7)

- `services/config.py` is the single source of truth for **every env-var name and
  default** (`AI_PROVIDER`/`AI_MODEL`/`DETECTOR`/`ANALYSIS_CACHE`/`SUPABASE_*`/…,
  and defaults `"mock"`/`"claude_vision"`/model names). Modules reference these
  constants instead of hardcoding strings; providers still read their own secrets.
  Resolvers: `resolved_provider()`, `resolved_detector()`, `env_flag()`.
- `services/registry.py` — one generic `Registry[T]` behind providers, detectors,
  and extractors. Unknown key raises (providers/detectors) or falls back
  (extractors, via `fallback=EmptyDetailExtractor`); that policy is the only
  difference and it's a constructor argument, not duplicated code.
- `services/text_utils.py` (`clean`, `rule_id_from_call_type`) and
  `services/verdicts.py` (`VERDICTS`, `normalize_verdict`) hold formerly-duplicated
  helpers/verdict maps. Interface style: providers use an ABC (`AIProvider`, for the
  shared `is_mock`); detectors/extractors use `Protocol`s — intentional, documented.

### Judging docs & UX hardening (Sprint 8)

- `docs/` holds the judge-facing deliverables: `JUDGE_CHEAT_SHEET.md`, `DEMO_WALKTHROUGH.md`, `ARCHITECTURE.md` (mermaid system + sequence diagrams), `TROUBLESHOOTING.md`, and `DEPLOYMENT_CHECKLIST.md`. The README links to all of them from a "For judges" section.
- `frontend/src/lib/referees.ts` is the single source of truth for the demo referee roster + the `/ref/<slug>` slug helper (previously duplicated across `Leaderboard`/`RefLeaderboards`/`Feed`, and `RefProfile` ignored the slug and always rendered one referee). `RefProfile` now resolves the ref by slug and shows a graceful "REF NOT FOUND" empty state for unknown slugs.
- `frontend/src/lib/api.ts` surfaces friendly error copy instead of raw `TypeError: Failed to fetch` / server HTML, and `getFeedItems()` never throws (a down backend yields an empty list, so the Feed falls back to demo clips).

### Deployment

- **Backend → Render**: `render.yaml` at repo root; rootDir=`backend`; `runtime: docker` (`backend/Dockerfile` → `uvicorn main:app`). There is no `build.sh`.
- **Frontend → Vercel**: root directory=`frontend`; framework auto-detected as Next.js; env var=`NEXT_PUBLIC_API_BASE`

## Key Constraints

- The response is built as dicts in `services/ai_analyzer.py` (`_build_response`/`_frontend_perception`); keep `frontend/src/lib/types.ts` in sync when the shape changes. There is no `schemas.py`.
- The Anthropic model default `claude-sonnet-4-5` lives in `backend/services/ai/providers/anthropic_provider.py` (`DEFAULT_MODEL`, sourced from `config.DEFAULT_ANTHROPIC_MODEL`), overridable via `AI_MODEL`. It is intentionally not updated yet — check before changing. Provider-specific model names belong in the provider classes, never in `ai_analyzer.py`.
- `_retrieve_rules()` scores the static corpus from `rules.sport_config` (keyword-based, no index files). The process must start from `backend/` so lazy `rules.*` imports resolve.
- Render free tier sleeps after 15 min inactivity. Hit `/api/health` before a demo to warm up.
