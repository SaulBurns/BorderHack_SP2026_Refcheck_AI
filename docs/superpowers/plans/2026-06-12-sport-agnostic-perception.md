# Sport-Agnostic Perception Schema & Detector Abstraction — Implementation Plan

> **Status:** Design + plan only. No application code is changed by this document.
> **Baseline:** HEAD `c919198` (sport-aware routing migration complete).
> **For agentic workers:** Use `superpowers:executing-plans` or `superpowers:subagent-driven-development`. Steps use checkbox (`- [ ]`) syntax. Each phase is independently committable; Phases 2+3 must ship together.

**Goal:** Replace the basketball-shaped perception schema with a sport-agnostic core + per-sport `sport_details` extension, and introduce a `Detector` abstraction so Claude Vision (today), YOLOv8 (next), and future detectors are interchangeable behind one seam — without changing basketball behavior.

**Non-goals:** Authoring hockey/soccer/lacrosse *rules*; training YOLO weights; changing adjudication logic. Those are downstream of this plan.

---

## 1. Current perception architecture (audit)

The perception contract lives in **three unsynchronized places** (there is no shared schema module — the `types.ts` header reference to `backend/app/models/schemas.py` is **stale; that file does not exist**):

| Layer | Location | Role |
|------|----------|------|
| Producer (LLM) | `backend/services/ai_analyzer.py` `_BASKETBALL_PERCEPTION_PROMPT` (L30–121) + `_make_stub_perception_prompt()` (L198–260) | Emits perception JSON |
| Normalizer | `ai_analyzer.py` `_frontend_perception()` (L957–1012) | Authoritative response shape; defaults missing fields |
| Consumer contract | `frontend/src/lib/types.ts` `EventDescription` (L16–54) | Rendered by `Verdict.tsx` |

Flow: `analyze_clip(sport)` → `_run_four_agent_pipeline` → `_perception_agent(frame_paths, original_call, sport)` → `_get_perception_prompt(sport)` → Claude Vision over 10 frames → JSON → `_frontend_perception(..., sport)` → `verdict.perception` → `Verdict.tsx`.

**Key constraint:** the stub prompts for hockey/soccer/lacrosse already emit the **basketball-shaped** JSON (court_zone, defender_status, court_geometry) with `"unclear"` values — so non-basketball sports are forced into basketball geometry today.

---

## 2. Basketball-specific assumptions

### 2a. Backend perception prompts (`ai_analyzer.py`)
- `_BASKETBALL_PERCEPTION_PROMPT`: court-zone taxonomy (`restricted_area / paint_lane / perimeter / beyond_arc / backcourt_or_unclear`), restricted-area legality, defender legal-guarding checklist, basket/rim references, `event_type` vocabulary (`possible_charge / travel / goaltending / three_seconds_violation`).
- `_make_stub_perception_prompt(sport)`: **inherits the basketball JSON shape** — emits `court_zone`, `defender_status{}`, `court_geometry{}` even for hockey/soccer/lacrosse.

### 2b. Perception response schema (`_frontend_perception` + `EventDescription`)
Basketball-specific fields:

| Field | Basketball-only reason |
|------|------------------------|
| `players_involved[].court_zone` | `restricted_area / paint_lane / perimeter / beyond_arc` |
| `ball_state` (values) | `dribbling / gathered / upward_motion` |
| `offensive_control_status` (whole field) | `dribbling / airborne_shooter / loose_ball` |
| `defender_status{}` (whole block) | `legal_guarding_position`, `inside_restricted_area`, `primary_or_secondary`, `feet_set_before_contact` |
| `court_geometry{}` (whole block) | `restricted_area_arc_visible`, `basket_visible`, `key_zone` |
| `event_type` (vocabulary) | basketball foul/violation names |

Sport-neutral (keep in core): `sport, summary, players_involved.{role, jersey_color, position_description, body_state}, contact_detected, contact_location, ball_visible, frame_observations, moment_of_interest_seconds, impact_zone, visual_quality, perception_confidence, notes`.

### 2c. Frontend rendering (`Verdict.tsx`)
`reviewChecklist` (L95–130) has **two basketball-coupled rows**:
- **"Court zone known"** → `v.perception.court_geometry?.key_zone` (L112–118)
- **"Defender status"** → `v.perception.defender_status?.legal_guarding_position` (L119–125)

Sport-neutral rows: Contact identified, Ball visible, Camera usable, Rule cited, Agents agree. Also: hardcoded `"Basketball ·"` header label (L189) and `impact_zone` overlay (neutral, L86–94).

---

## 3. Sport-agnostic perception model

### 3a. Common core (every sport always populates)
```
PerceptionCore:
  schema_version: int               # bump on breaking changes; gates cache + validation
  sport: str
  event_type: str                   # value vocabulary defined per-sport in sport_config
  summary: str
  players_involved: [Player]
  contact: Contact
  object_of_play: ObjectOfPlay      # generalizes ball_visible / ball_state
  frame_observations: [FrameObservation]
  moment_of_interest_seconds: float | null
  impact_zone: ImpactZone
  visual_quality: "clear|partial|obstructed|poor"
  perception_confidence: float       # 0..1
  notes: str | null
  detections: RawDetections | null   # optional structured detector output (see §5)
  sport_details: SportDetails        # per-sport extension (registry-validated)

Player:        { role, team_color, position_description, body_state, zone: str | null }
Contact:       { detected: bool, location: str, severity: "incidental|significant|unclear|none" }
ObjectOfPlay:  { kind: "ball|puck", visible: bool, state: str }   # state vocabulary per-sport
ImpactZone:    { x_percent, y_percent, radius_percent, label }
FrameObservation: { frame_index, approx_time_seconds, observation }
```
`zone` on `Player` is a **generic string** whose vocabulary is sport-defined (basketball: `paint_lane`; hockey: `offensive_zone`; soccer: `attacking_third`), so the core stays neutral while preserving per-sport meaning.

### 3b. `sport_details` — registry-validated extension
Mirrors the existing `_PERCEPTION_PROMPTS` dict pattern:
```
SPORT_DETAIL_MODELS: dict[str, type[SportDetails]] = {
  "basketball": BasketballDetails,   # offensive_control_status, defender_status{}, court_geometry{}
  "hockey":     HockeyDetails,       # zone, goalie_involved, puck_possession,
                                     #   infraction_candidate, boards_involved
  "soccer":     SoccerDetails,       # field_third, in_penalty_area, offside_relevant,
                                     #   last_defender, handball_candidate, foul_direction
  "lacrosse":   LacrosseDetails,     # crease_violation, cross_check, slashing,
                                     #   ball_carrier_status, warding
}

def get_sport_details_model(sport: str) -> type[SportDetails]:
    return SPORT_DETAIL_MODELS.get(sport, EmptySportDetails)   # stub fallback, like _get_perception_prompt
```
- **`BasketballDetails` is lossless**: today's `offensive_control_status`, `defender_status{}`, `court_geometry{}` move verbatim under `sport_details.basketball`.
- Hockey/soccer/lacrosse get minimal models (all fields optional/`unclear`) — consistent with current empty-rules routing.

### 3c. Why this shape (maintainability)
- **Open/Closed:** adding a sport = add one `*Details` model + one registry entry + one prompt; no edits to core or pipeline.
- **Single source of truth:** Pydantic models replace hand-built dicts; `types.ts` is generated/mirrored from them.
- **Backward compatible reasoning:** the adjudicator already receives the full perception dict; it keeps working as long as `sport_details.basketball` carries the same keys.

---

## 4. Detector abstraction layer

A `Detector` is "eyes only" — it turns frames into a `PerceptionCore` (+ optional `RawDetections`). Selected by registry/flag exactly like `AI_PROVIDER`/prompt dicts.

```
class Detector(Protocol):
    name: str
    def detect(self, frames: list[Path], sport: str, original_call: str) -> DetectorResult: ...

DetectorResult: { core: PerceptionCore, raw: RawDetections | None }

DETECTORS = {
  "claude_vision": ClaudeVisionDetector,   # wraps today's _perception_agent (no behavior change)
  "yolov8":        YoloDetector,           # new; emits core + raw detections
}
def get_detector(name: str) -> Detector: ...   # default "claude_vision"
```
- **`SportDetailExtractor[sport]`** is a second, sport-keyed seam that converts `RawDetections` (+ optional LLM pass over detector priors) into `sport_details`. This keeps geometry interpretation (court keypoints → `key_zone`) out of the detector core.
- **Composability:** detectors can chain — e.g. `YoloDetector` fills `players_involved`/`object_of_play`/`impact_zone`/`detections`, then `ClaudeVisionDetector` reasons over those priors to fill `summary`, `event_type`, and `sport_details`. A `HybridDetector` composes the two.
- **Config:** `DETECTOR=claude_vision|yolov8|hybrid` env var; default preserves current behavior.

---

## 5. YOLOv8 → schema mapping

YOLOv8 emits per-frame `{class, confidence, bbox, track_id}`. New optional core block:
```
RawDetections:
  model: str                 # "yolov8n" / custom weights id
  detector_version: str
  frames: [{ frame_index, objects: [{ label, confidence, bbox_norm{x,y,w,h}, track_id }] }]
```

| YOLO output | Schema target | Mechanism |
|-------------|---------------|-----------|
| `person` boxes + tracks | `players_involved[]`, `detections.objects` | jersey crop → `team_color`; track kinematics → `body_state` |
| `sports ball` / puck class | `object_of_play.{visible}` + bbox in `detections` | hockey needs a puck-trained class/weights |
| ball–player proximity / track kinematics | `moment_of_interest_seconds`, `impact_zone` | peak proximity or velocity-change frame |
| player-pair bbox IoU spike | `contact.detected`, `impact_zone` | overlap threshold |
| court/rink/field keypoints (pose/seg model) | `sport_details.*` zones (`key_zone`, hockey `zone`, soccer `field_third`/`in_penalty_area`) | per-sport `SportDetailExtractor` |

YOLO does **not** decide verdicts or fill `summary`/`event_type` — those remain LLM/adjudicator responsibilities. YOLO supplies *measured priors*; Claude consumes them, replacing today's estimated geometry.

---

## 6. Migration requirements

### Backend
- New `backend/services/perception_schema.py` (Pydantic v2): core models + `SportDetails` base + per-sport models + `SPORT_DETAIL_MODELS` registry + `get_sport_details_model`.
- New `backend/services/detectors/` package: `Detector` protocol, `ClaudeVisionDetector` (wraps current `_perception_agent`), `DETECTORS` registry, `get_detector`. `YoloDetector` added in a later phase.
- `_BASKETBALL_PERCEPTION_PROMPT` updated to emit `sport_details.basketball{}` instead of top-level basketball blocks; stub prompts emit empty `sport_details`.
- `_frontend_perception()` / `_build_response()` restructured to core + `sport_details`.
- Tests: `tests/test_perception_schema.py`, extend `tests/test_sport_routing.py`.

### Frontend
- `types.ts`: split `EventDescription` into core + `sport_details: SportDetails` discriminated union (`BasketballDetails | HockeyDetails | SoccerDetails | LacrosseDetails`); generalize `ball_*` → `object_of_play`; `PlayerObservation.court_zone` → optional `zone`; add optional `detections`; add `schema_version`; fix stale schema header.
- `Verdict.tsx`: replace the two basketball-coupled checklist rows with a per-sport `sportEvidenceRows[sport](perception) => Row[]` config (basketball keeps its two rows from `sport_details.basketball`); de-hardcode `"Basketball ·"` → `v.perception.sport`.
- `Upload.tsx`: list all four backend sports (currently basketball-only) — required for the multi-sport MVP, can ship independently.
- Bump the `sessionStorage` cache key (`refcheck:verdict:`) tied to `schema_version` so cached old-shape verdicts don't render against the new type.

---

## 7. Implementation plan (phased, TDD)

### Phase 0 — Formalize the contract (additive, safe)
- [ ] Create `perception_schema.py` with core Pydantic models (no `sport_details` yet); add `tests/test_perception_schema.py` (roundtrip + validation).
- [ ] Add a characterization test capturing today's basketball `_frontend_perception` output verbatim (golden snapshot) to guarantee zero behavior drift later.

### Phase 1 — Sport-details registry (additive)
- [ ] Add `SportDetails` base, `BasketballDetails` (existing fields, lossless), minimal `Hockey/Soccer/Lacrosse/EmptySportDetails`, `SPORT_DETAIL_MODELS`, `get_sport_details_model`.
- [ ] Tests mirroring `test_sport_routing`: basketball returns populated model; others return empty; unknown → stub.

### Phase 2 — Rewire producer + normalizer (coordinated breaking change — backend half)
- [ ] Update `_BASKETBALL_PERCEPTION_PROMPT` to nest basketball blocks under `sport_details`.
- [ ] Restructure `_frontend_perception` / `_build_response` to emit core + `sport_details`; set `schema_version`.
- [ ] Golden test: basketball response is field-equivalent (relocated, none lost). Full `pytest` green.

### Phase 3 — Frontend contract (coordinated breaking change — frontend half; ship with Phase 2)
- [ ] Update `types.ts` (core + discriminated `SportDetails`, `object_of_play`, `zone`, `detections`, `schema_version`); fix stale header.
- [ ] `Verdict.tsx`: `sportEvidenceRows` config; de-hardcode sport label; bump cache key.
- [ ] `tsc` clean + render smoke test for basketball verdict.

### Phase 4 — Detector seam (refactor, no behavior change)
- [ ] Add `Detector` protocol + `ClaudeVisionDetector` wrapping current perception; `DETECTORS` registry; `get_detector` (default `claude_vision`).
- [ ] Route `_run_four_agent_pipeline` through `get_detector(...)`. Tests assert identical output to Phase 2 golden.

### Phase 5 — YOLOv8 adapter (feature-flagged, off by default)
- [ ] Add `YoloDetector` + `RawDetections` population + per-sport `SportDetailExtractor`; `DETECTOR=yolov8|hybrid` flag.
- [ ] Integration test on a sample clip (mock weights ok); default path unchanged.

### Phase 6 — Prove generalization (second sport)
- [ ] Implement `HockeyDetails` end-to-end + a small hockey rules dataset; validate the full seam on hockey.

---

## 8. Self-review

**Preserves basketball behavior:** Phase 0 golden snapshot + Phase 2/4 equivalence tests guarantee the basketball response is byte-equivalent modulo field relocation; `BasketballDetails` is a verbatim move.

**Extensibility:** new sport = `*Details` model + registry entry + prompt (3 touch points, all additive). New detector = one class + registry entry. No core/pipeline edits.

**Maintainability:** Pydantic models become the single source of truth; `types.ts` mirrors them; the stale schema-path header is corrected.

**Risk register:**
- *Breaking response shape* — confined to Phase 2+3, gated by `schema_version` + cache-key bump; ship together.
- *Adjudicator depends on perception dict* — mitigated by lossless `sport_details.basketball` keys; add an adjudicator-input contract test.
- *YOLO scope creep* — isolated behind a flag (Phase 5), default path untouched.
- *Schema desync (backend↔frontend)* — add a CI check comparing `schema_version` constants in both trees.

**Open decisions for review:**
1. `sport_details` as a typed discriminated union vs. a validated `dict[str, Any]` — recommend typed union for frontend safety.
2. Whether to formalize the *entire* response (adjudicators, verdict) into Pydantic in Phase 0, or only perception — recommend perception-only now to bound scope.
3. Detector composition model — recommend `HybridDetector` (YOLO priors → Claude reasoning) as the eventual default once YOLO lands.
