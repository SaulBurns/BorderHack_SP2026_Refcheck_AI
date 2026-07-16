# RefCheck AI — Backend Architecture Summary

A multi-agent pipeline that reviews a sports officiating call: a clip comes in,
four LLM agents perceive → retrieve rules → adjudicate (×2) → reconcile, and a
structured verdict comes out. Everything runs against Anthropic, Gemini, or an
offline **mock** with no code change — selected by the `AI_PROVIDER` env var.

## Request flow

```
main.py  (FastAPI)
  POST /api/analyze ──asyncio.to_thread──▶ services/ai_analyzer.py: analyze_clip()
                                                │
        frames  ◀── services/analysis/frames.py │ (ffprobe+ffmpeg, disk-cached)
                                                ▼
                       _run_four_agent_pipeline()
        detector ── services/detectors/ ──▶ perception dict
        query    ── _retrieval_agent (LLM)
        rules    ── services/analysis/retrieval.py (keyword scoring, no embeddings)
        verdicts ── adjudicator A ∥ B  (ThreadPoolExecutor, one shared prompt)
                                                │
                       _build_response() → _reconcile()
                                                ▼
        persist ── services/supabase_store.py ──▶ JSON response (mirrors frontend types)
```

## Service boundaries

| Layer | Package | Responsibility | Swap seam |
| --- | --- | --- | --- |
| HTTP | `main.py` | routes, CORS, thread offload, persistence call | — |
| Orchestration | `services/ai_analyzer.py` | the 4-agent flow, caches, reconciliation, response build | — |
| Pipeline internals | `services/analysis/` | prompts, frames, retrieval, mock result, diagnostics, contracts | — |
| LLM providers | `services/ai/` | Anthropic / Gemini / mock behind `AIProvider` | `AI_PROVIDER` |
| Perception detectors | `services/detectors/` | claude_vision / yolov8 / hybrid behind `Detector` | `DETECTOR` |
| Sport detail extractors | `services/extractors/` | detections → per-sport `SportDetails` | by `sport` |
| Game metadata | `services/metadata/` | optional NBA game-context enrichment (guarded) | by `sport` |
| Config | `services/config.py` | every env-var name + default, in one place | — |
| Shared kernel | `services/registry.py`, `text_utils.py`, `verdicts.py`, `perception_schema.py` | generic registry, string/verdict helpers, Pydantic detail models | — |

**Rule of the provider/detector/extractor seams:** a plugin only knows how to do
its one job (turn inputs into an output). It must not import `ai_analyzer`, know
about agents, or reshape the response. Selection is env-driven through the shared
`Registry` (`services/registry.py`); an unknown provider/detector fails loudly, an
unknown sport for extractors falls back to an empty extractor.

## Key design decisions

- **Provider-agnostic pipeline.** The orchestrator touches LLMs only through
  `_send_messages` → `AIProvider.send_messages`, and parses replies with one
  shared `_extract_json`. Vendor HTTP/SDK/auth/image-encoding stays in the
  provider classes.
- **Keyword retrieval, not embeddings.** Rules are scored by keyword overlap +
  hand-tuned boosts over the static `rules.sport_config` corpus. There is no
  FAISS/`sentence-transformers` (despite older docs) — corpus and ranking are
  `@lru_cache`d instead.
- **Two adjudicators, reconciled.** A conservative (temp 0.2) and a skeptical
  (temp 0.7) reviewer run concurrently on identical evidence; agreement raises
  confidence, disagreement or weak perception forces `inconclusive`.
- **Graceful degradation.** Missing key, ffmpeg failure, or a per-agent error
  degrades to the canned `mock_result`; the API always returns a valid verdict.
- **Additive enrichment.** YOLO tracked evidence, sport details, game context, and
  diagnostics are layered on without changing the core verdict contract.

## Typing & contracts

`services/analysis/contracts.py` defines `TypedDict`s (`RuleRecord`,
`AdjudicatorOutput`, `AgentResult`) for the payloads that flow between stages.
Perception stays an open dict (model-produced, read defensively). The response
shape has no server-side schema class — `frontend/src/lib/types.ts` is its mirror
and must be kept in sync.

## Where to make common changes

- **Add a provider** → new class in `services/ai/providers/` + one `register` line in `factory.py`.
- **Add a detector** → new class in `services/detectors/` + `registry.register` in `detectors/registry.py`.
- **Add/edit rules** → `rules/…` (loaded via `rules.sport_config`).
- **Change a prompt** → `services/analysis/prompts.py`.
- **Change an env var / default** → `services/config.py` only.

See `CLAUDE.md` for commands and `PERFORMANCE.md` for the Sprint 6 optimizations.
