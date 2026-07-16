# Curated demo clips

`manifest.json` describes a small, curated suite of **basketball** clips used for
sponsor-facing demos. `soccer_manifest.json` (Sprint 10) is the matching
**soccer** suite (7 scenarios: foul, offside, handball, penalty, red card, yellow
card, goal). Run either with:

```bash
cd backend
python scripts/run_demo_suite.py --manifest demo_clips/manifest.json --provider mock
python scripts/run_demo_suite.py --manifest demo_clips/soccer_manifest.json --provider mock
```

## ⚠️ Placeholder media

The `*.mp4` files checked in here are **tiny placeholders** (a valid MP4 header,
no real footage). They exist only so the suite runner executes end-to-end and
produces a report in environments without real clips. Because they contain no
decodable frames — and because a real run also needs `ffmpeg` + `ANTHROPIC_API_KEY`
— running against these placeholders always degrades to the transparent **mock**
path, which the report labels honestly (`REAL PIPELINE RAN: NO`).

**To produce a real sponsor demo:** drop the real clips in this folder using the
filenames referenced by `manifest.json` (or edit `video_path`), install `ffmpeg`
and `ultralytics`, set `ANTHROPIC_API_KEY`, and run with
`--provider anthropic --detector claude_vision` (add `--strict-real` to refuse any
mock fallback).

## Manifest schema

Each entry supports:

| field             | required | meaning                                             |
|-------------------|----------|-----------------------------------------------------|
| `clip_id`         | yes      | Stable identifier for the clip.                     |
| `sport`           | yes      | Sport key (e.g. `basketball`).                      |
| `video_path`      | yes      | Path to the clip (relative to `backend/` or manifest dir). |
| `original_call`   | yes      | The officiating call under review.                  |
| `expected_verdict`| no       | `fair_call` \| `bad_call` \| `inconclusive` (sponsor synonyms like `upheld`/`overturned` are accepted). |
| `game_date`       | no       | `YYYY-MM-DD` metadata hint.                          |
| `home_team`       | no       | Home team hint (abbr or name), e.g. `LAL`.          |
| `away_team`       | no       | Away team hint (abbr or name), e.g. `BOS`.          |
| `notes`           | no       | Free-text note shown in reports.                    |
