# RefCheck AI — Judge Cheat Sheet

One page. What it is, why it's hard, and where to look.

## The pitch (30 seconds)

Upload a short basketball clip + the call the ref made. RefCheck AI runs a
**four-agent AI pipeline** — it *sees* the play, *looks up* the relevant rule, has
**two independent adjudicators** argue it from opposite biases, then **reconciles**
them into a verdict: **fair call / bad call / inconclusive**, with confidence, a cited
rule, and the reasoning. It runs on **Anthropic, Gemini, or fully offline** — switching
is one environment variable.

## Why this is more than a prompt wrapper

| Differentiator | Where it lives |
|---|---|
| **Four specialized agents**, not one prompt — perception → retrieval → two adjudicators → reconciliation | `services/ai_analyzer.py` |
| **Provider abstraction** — Anthropic / Gemini / Mock behind one interface; add a provider in ~15 lines | `services/ai/` |
| **Hybrid CV grounding** — YOLO tracked detections (players, ball, possession, movement) feed both adjudicators and calibrate confidence, but never override the semantic verdict | `services/extractors/basketball_vision.py` |
| **Graceful degradation everywhere** — no key / no ffmpeg / no GPU still returns a labeled result; failures are surfaced in `diagnostics`, never hidden | `services/ai_analyzer.py`, `services/detectors/hybrid.py` |
| **Honest evaluation harness** — accuracy, precision/recall/F1, confusion matrix, **confidence calibration (ECE)**, latency, and **provider comparison** with HTML/MD reports | `evaluation/` |
| **Curated demo suite** — 10 officiating scenarios, one command, aggregate metrics report | `scripts/run_demo_suite.py` |
| **AI reasoning overlay** — tracked players/ball, impact zone, movement arrows, confidence heatmap, possession + event timelines on the clip | `frontend/src/app/components/AiReasoningPanel.tsx` |
| **~410 backend tests**, TDD throughout | `backend/tests/` |

## Run it in 60 seconds (no keys needed)

```bash
# Backend (offline mock — always works)
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
AI_PROVIDER=mock uvicorn main:app --port 8000
```
```bash
# One-command sponsor demo (10 scenarios → metrics report)
cd backend && python scripts/run_demo_suite.py
```
```bash
# Provider-comparison benchmark (accuracy, calibration, latency, HTML report)
cd backend && python -m evaluation \
  --dataset data/eval/benchmark_basketball.json \
  --providers mock --output bench.json --md bench.md --html bench.html
```

For the full UI: run the frontend (`cd frontend && npm run dev`) and open
`http://localhost:3000`. See [DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md).

## What to look at

1. **Verdict screen** — the AI reasoning overlay on the clip + the two adjudicators
   ("How We Decided") + the cited rule.
2. **`diagnostics` block** in the API response — proves whether the real pipeline ran,
   which provider/detector, whether YOLO influenced the decision, and why anything
   fell back. RefCheck never fakes a real run.
3. **`scripts/run_demo_suite.py` report** — verdict/rule/confidence accuracy across the
   10 curated scenarios.
4. **`evaluation/` HTML report** — a real ML evaluation with a confusion matrix and
   calibration, comparing providers side by side.

## The honest caveats (we say them out loud)

- The checked-in demo clips are **tiny placeholders** (valid MP4 header, no footage) so
  everything runs anywhere; drop real footage in for a live demo.
- Rules are a **hand-authored keyword corpus** (no embeddings/FAISS) — small, fast, and
  transparent, scoped to basketball.
- Tracked player/ball markers in the overlay use an **impact-zone-anchored reasoning
  layout** (the backend doesn't expose raw CV boxes) and are labeled approximate; the
  impact zone, confidence, possession, and timelines are real response data.

## Architecture in one line

`clip → ffmpeg frames → perception → rule retrieval → adjudicator A ∥ B → reconcile →
verdict + cited rule + diagnostics`. Diagram: [ARCHITECTURE.md](ARCHITECTURE.md).
