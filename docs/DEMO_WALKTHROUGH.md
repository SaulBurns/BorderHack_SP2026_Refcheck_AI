# RefCheck AI — Demo Walkthrough

Three ways to demo, shortest first. All run **offline in mock mode** with zero API
keys — swap in a real provider (`AI_PROVIDER=anthropic|gemini`) for the live pipeline.

---

## Demo 1 — One command (fastest, no UI)

Runs the curated 10-scenario suite through the real `analyze_clip` pipeline and prints
a metrics report.

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # first time only
pip install -r requirements.txt                     # first time only
python scripts/run_demo_suite.py
```

You'll see a per-clip summary and a written report at
`demo_reports/demo_report.md` (+ `.json`) with **verdict accuracy, rule-citation
accuracy, confidence-expectation rate, scenario coverage, and verdict distribution**.

- One scenario: `python scripts/run_demo_suite.py --clip-id nba_goaltending_07`
- Real pipeline, refuse to fake it: `python scripts/run_demo_suite.py --provider anthropic --detector hybrid --strict-real`

> The demo clips are placeholders, so mock mode labels every clip honestly
> (`REAL PIPELINE RAN: NO`). Drop real footage into `backend/demo_clips/` for a live run.

---

## Demo 2 — The evaluation benchmark (the "we measure ourselves" story)

```bash
cd backend && source venv/bin/activate
python -m evaluation \
  --dataset data/eval/benchmark_basketball.json \
  --providers mock \
  --output bench.json --md bench.md --html bench.html
open bench.html   # provider comparison + confusion matrix + calibration + latency
```

Add `anthropic,gemini` to `--providers` (with keys set) for a side-by-side provider
comparison table.

---

## Demo 3 — Full UI (the visual story)

### Start both servers

```bash
# Terminal 1 — backend (mock)
cd backend && source venv/bin/activate
AI_PROVIDER=mock uvicorn main:app --reload --port 8000
```
```bash
# Terminal 2 — frontend
cd frontend
npm install            # first time only
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local   # first time only
npm run dev
```

Open **http://localhost:3000**.

### The click-through (2–3 minutes)

1. **Home** → *Analyze a clip*.
2. **Upload** — pick any short video, choose **Basketball**, type the call the ref made
   (e.g. *"Blocking foul on the defender"*), submit. A loading state runs while the
   backend analyzes.
3. **Verdict** — the money screen:
   - **Verdict banner** (fair/bad/inconclusive) + confidence.
   - **AI Reasoning Overlay** on the clip — toggle layers: tracked players, ball, impact
     zone, movement arrows, confidence heatmap; scrub the **possession** and **event
     timelines**; use **key-frame navigation** to jump the video.
   - **Ref Review Checklist** — what the AI verified.
   - **Rule Cited** — the specific rule the verdict rests on.
   - **How We Decided** — expand to see **both adjudicators** and the reconciliation note.
4. **Feed / Leaderboard / Ref profiles** — the community layer (demo data; the feed
   falls back gracefully if the backend is down).

### Talking points while it loads

- "There are **four agents** here, not one prompt — and two of them argue from opposite
  biases, then get reconciled."
- "It's provider-agnostic — this exact flow runs on Claude, Gemini, or fully offline."
- "The `diagnostics` block in the response tells you whether the *real* pipeline ran —
  we never fake it."

---

## If something goes wrong

The demo is built to never hard-fail: no key/ffmpeg/GPU → transparent mock fallback,
backend down → the Feed shows demo clips, a bad clip → a friendly error, not a stack
trace. If you still hit trouble, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
