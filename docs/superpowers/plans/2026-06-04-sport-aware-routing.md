# Sport-Aware Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every basketball-hardcoded constant, function signature, and output string in the AI pipeline with sport-keyed structures so any registered sport is routed correctly without changing AI logic.

**Architecture:** A new `backend/rules/sport_config.py` owns sport registration (display names and rules data). The three prompt constants in `ai_analyzer.py` are renamed with a `_BASKETBALL_` prefix, and sport-keyed dicts plus stub generators cover the four registered sports. Every pipeline function gains a `sport: str` parameter threaded from `analyze_clip()` at the top down to the individual agent calls at the bottom. Output formatting functions stop hardcoding `"basketball"`.

**Tech Stack:** Python 3.11, FastAPI, pytest (no new dependencies)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/rules/sport_config.py` | **Create** | SPORTS registry; `normalize_sport()`; `get_rules_for_sport()` |
| `backend/tests/__init__.py` | **Create** | Makes `tests/` a Python package |
| `backend/tests/test_sport_routing.py` | **Create** | All sport-routing unit tests |
| `backend/services/ai_analyzer.py` | **Modify** | Prompt constants renamed; prompt dicts added; all pipeline functions gain `sport` param; hardcoded output strings fixed |

---

## Task 1 — Create `sport_config.py` and the test scaffold

**Files:**
- Create: `backend/rules/sport_config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_sport_routing.py`

- [ ] **Step 1: Create the tests directory**

```bash
cd backend
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 2: Write failing tests for `normalize_sport` and `get_rules_for_sport`**

Create `backend/tests/test_sport_routing.py`:

```python
import sys
import os

# Run from backend/ so imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from rules.sport_config import normalize_sport, get_rules_for_sport, SPORTS


# ---------------------------------------------------------------------------
# normalize_sport
# ---------------------------------------------------------------------------

def test_normalize_sport_lowercase():
    assert normalize_sport("basketball") == "basketball"

def test_normalize_sport_titlecase():
    assert normalize_sport("Basketball") == "basketball"

def test_normalize_sport_uppercase():
    assert normalize_sport("HOCKEY") == "hockey"

def test_normalize_sport_strips_whitespace():
    assert normalize_sport("  soccer  ") == "soccer"

def test_normalize_sport_unknown_falls_back_to_basketball():
    assert normalize_sport("curling") == "basketball"

def test_normalize_sport_empty_string_falls_back():
    assert normalize_sport("") == "basketball"


# ---------------------------------------------------------------------------
# get_rules_for_sport
# ---------------------------------------------------------------------------

def test_get_rules_basketball_returns_nonempty_dict():
    rules = get_rules_for_sport("basketball")
    assert len(rules) > 0

def test_get_rules_basketball_has_block_charge():
    rules = get_rules_for_sport("basketball")
    assert "block_charge" in rules

def test_get_rules_hockey_returns_empty_dict():
    assert get_rules_for_sport("hockey") == {}

def test_get_rules_soccer_returns_empty_dict():
    assert get_rules_for_sport("soccer") == {}

def test_get_rules_lacrosse_returns_empty_dict():
    assert get_rules_for_sport("lacrosse") == {}

def test_get_rules_unknown_sport_returns_empty_dict():
    assert get_rules_for_sport("curling") == {}


# ---------------------------------------------------------------------------
# SPORTS registry shape
# ---------------------------------------------------------------------------

def test_sports_has_exactly_four_entries():
    assert set(SPORTS.keys()) == {"basketball", "hockey", "soccer", "lacrosse"}

def test_sports_entries_have_display_name():
    for key, config in SPORTS.items():
        assert "display_name" in config, f"{key} missing display_name"

def test_sports_entries_have_rules_key():
    for key, config in SPORTS.items():
        assert "rules" in config, f"{key} missing rules key"
```

- [ ] **Step 3: Run tests — verify they ALL fail**

```bash
cd backend && source venv/bin/activate
pytest tests/test_sport_routing.py -v 2>&1 | head -30
```

Expected output: `ModuleNotFoundError: No module named 'rules.sport_config'`

- [ ] **Step 4: Create `backend/rules/sport_config.py`**

```python
from rules.basketball_rules import BASKETBALL_RULES

SPORTS: dict[str, dict] = {
    "basketball": {
        "display_name": "Basketball",
        "rules": BASKETBALL_RULES,
    },
    "hockey": {
        "display_name": "Hockey",
        "rules": {},
    },
    "soccer": {
        "display_name": "Soccer",
        "rules": {},
    },
    "lacrosse": {
        "display_name": "Lacrosse",
        "rules": {},
    },
}

SUPPORTED_SPORTS: frozenset[str] = frozenset(SPORTS)


def normalize_sport(sport: str) -> str:
    """Lowercase and strip the value; return 'basketball' for unrecognized sports."""
    normalized = sport.lower().strip() if sport else ""
    return normalized if normalized in SPORTS else "basketball"


def get_rules_for_sport(sport: str) -> dict:
    """Return the rules dict for a sport. Empty dict for unimplemented sports."""
    return SPORTS.get(normalize_sport(sport), {}).get("rules", {})
```

- [ ] **Step 5: Run tests — verify they ALL pass**

```bash
pytest tests/test_sport_routing.py -v
```

Expected: `15 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/rules/sport_config.py backend/tests/__init__.py backend/tests/test_sport_routing.py
git commit -m "feat: add sport_config registry with normalize_sport and get_rules_for_sport"
```

---

## Task 2 — Add sport-keyed prompt dicts and selector functions

**Files:**
- Modify: `backend/services/ai_analyzer.py` (lines 30–189: the three prompt constants and framing strings)
- Modify: `backend/tests/test_sport_routing.py` (append prompt selector tests)

- [ ] **Step 1: Append failing prompt selector tests**

Add to the bottom of `backend/tests/test_sport_routing.py`:

```python
# ---------------------------------------------------------------------------
# Prompt selectors
# (These will ImportError until Task 2 is implemented.)
# ---------------------------------------------------------------------------

from services.ai_analyzer import (
    _get_perception_prompt,
    _get_retrieval_prompt,
    _get_adjudicator_prompt,
)


# --- _get_perception_prompt ---

def test_perception_prompt_basketball_contains_basketball_terms():
    prompt = _get_perception_prompt("basketball")
    assert "basketball" in prompt.lower()
    assert "restricted area" in prompt.lower()

def test_perception_prompt_hockey_does_not_mention_restricted_area():
    prompt = _get_perception_prompt("hockey")
    assert "restricted area" not in prompt.lower()

def test_perception_prompt_returns_nonempty_string_for_all_sports():
    for sport in ("basketball", "hockey", "soccer", "lacrosse"):
        result = _get_perception_prompt(sport)
        assert isinstance(result, str) and len(result) > 100, f"empty prompt for {sport}"


# --- _get_retrieval_prompt ---

def test_retrieval_prompt_basketball_mentions_basketball_specific_terms():
    prompt = _get_retrieval_prompt("basketball")
    assert any(
        term in prompt.lower()
        for term in ("pivot foot", "restricted area", "airborne shooter")
    )

def test_retrieval_prompt_hockey_does_not_mention_pivot_foot():
    prompt = _get_retrieval_prompt("hockey")
    assert "pivot foot" not in prompt.lower()

def test_retrieval_prompt_returns_nonempty_string_for_all_sports():
    for sport in ("basketball", "hockey", "soccer", "lacrosse"):
        result = _get_retrieval_prompt(sport)
        assert isinstance(result, str) and len(result) > 50, f"empty prompt for {sport}"


# --- _get_adjudicator_prompt ---

def test_adjudicator_prompt_basketball_mentions_nba():
    prompt = _get_adjudicator_prompt("basketball")
    assert "nba" in prompt.lower()

def test_adjudicator_prompt_hockey_does_not_mention_nba():
    prompt = _get_adjudicator_prompt("hockey")
    assert "nba" not in prompt.lower()

def test_adjudicator_prompt_returns_nonempty_string_for_all_sports():
    for sport in ("basketball", "hockey", "soccer", "lacrosse"):
        result = _get_adjudicator_prompt(sport)
        assert isinstance(result, str) and len(result) > 100, f"empty prompt for {sport}"
```

- [ ] **Step 2: Run just the new tests — verify they fail**

```bash
pytest tests/test_sport_routing.py -k "prompt" -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name '_get_perception_prompt'`

- [ ] **Step 3: In `ai_analyzer.py`, rename the three prompt constants**

Make these three find-and-replace changes (content unchanged, only names):

| Old name | New name |
|----------|----------|
| `PERCEPTION_SYSTEM_PROMPT` | `_BASKETBALL_PERCEPTION_PROMPT` |
| `RETRIEVAL_SYSTEM_PROMPT` | `_BASKETBALL_RETRIEVAL_PROMPT` |
| `ADJUDICATOR_BASE_SYSTEM_PROMPT` | `_BASKETBALL_ADJUDICATOR_PROMPT` |

Also update the two internal references that use the old names:
- Line ~408: `system_prompt=PERCEPTION_SYSTEM_PROMPT` → `system_prompt=_BASKETBALL_PERCEPTION_PROMPT`
- Line ~434: `system_prompt=RETRIEVAL_SYSTEM_PROMPT` → `system_prompt=_BASKETBALL_RETRIEVAL_PROMPT`
- Line ~548: `system_prompt=f"{ADJUDICATOR_BASE_SYSTEM_PROMPT}\n\n{framing}"` → `system_prompt=f"{_BASKETBALL_ADJUDICATOR_PROMPT}\n\n{framing}"`

- [ ] **Step 4: Add stub builders, prompt dicts, and selector functions after `SKEPTICAL_FRAMING`**

Insert this block immediately after the `SKEPTICAL_FRAMING` constant (around line 190):

```python
# ---------------------------------------------------------------------------
# Stub prompt builders for unimplemented sports.
# When a sport is fully implemented, replace the stub call in the dict below
# with a named constant (e.g. _HOCKEY_PERCEPTION_PROMPT = "...").
# ---------------------------------------------------------------------------

def _make_stub_perception_prompt(sport: str) -> str:
    return f"""
You are a sports video analyst reviewing {sport} officiating.

Your job is to describe what you observe in structured form. You are NOT issuing a verdict.
A separate agent will rule on the call. Be accurate and honest about what you can see.

OBSERVATION GUIDELINES:
Describe the players involved, their positions, any contact, and the key moment of the play.
Be honest about what you cannot see. Lower perception_confidence if footage is unclear.

OUTPUT FORMAT:
Output ONLY valid JSON. No prose, no markdown fences.
{{
  "sport": "{sport}",
  "event_type": "unclear",
  "summary": "2 to 4 sentences describing what happens in plain English",
  "players_involved": [
    {{
      "role": "offense | defense | unclear",
      "jersey_color": "color string or null",
      "position_description": "where they are",
      "court_zone": "backcourt_or_unclear",
      "body_state": "motion state at moment of interest"
    }}
  ],
  "contact_detected": false,
  "contact_location": "torso | arm | lower_body | unclear | none",
  "ball_visible": false,
  "ball_state": "unclear",
  "offensive_control_status": "unclear",
  "defender_status": {{
    "primary_or_secondary": "unclear",
    "legal_guarding_position": "unclear",
    "feet_set_before_contact": false,
    "moving_direction": "stationary | lateral | forward | backward | vertical | unclear",
    "inside_restricted_area": false
  }},
  "court_geometry": {{
    "key_zone": "backcourt_or_unclear",
    "restricted_area_arc_visible": false,
    "defender_feet_visible": false,
    "basket_visible": false
  }},
  "frame_observations": [
    {{
      "frame_index": 1,
      "approx_time_seconds": 0.0,
      "observation": "short concrete observation"
    }}
  ],
  "moment_of_interest_seconds": null,
  "impact_zone": {{
    "x_percent": 50,
    "y_percent": 50,
    "radius_percent": 14,
    "label": "key moment or contact point"
  }},
  "visual_quality": "clear | partial | obstructed | poor",
  "perception_confidence": 0.3,
  "notes": "Sport-specific perception guidelines for {sport} are not yet configured."
}}
""".strip()


def _make_stub_retrieval_prompt(sport: str) -> str:
    return f"""
You convert {sport} play descriptions into short rulebook search queries.

Output ONLY the search query as plain text. No preamble, no quotes, no markdown.
5 to 15 words.
Focus on the type of play, player actions, and any contact observed.
""".strip()


def _make_stub_adjudicator_prompt(sport: str) -> str:
    return f"""
You are a {sport} officiating reviewer.

You will be given a structured description of a play and any retrieved rules.
Issue a verdict on whether the original call was correct.

VALID VERDICTS:
- "fair_call": the original call was consistent with the rules, given the evidence
- "bad_call": the original call was inconsistent with the rules, given the evidence
- "inconclusive": the visual evidence or available rules are insufficient for a confident verdict

UNCERTAINTY DISCIPLINE:
If no rules are provided, return inconclusive with a flag noting the absence of rules.
If perception_confidence is below 0.5, lean toward inconclusive.

OUTPUT FORMAT:
Output ONLY valid JSON. No prose, no markdown fences.
{{
  "verdict": "fair_call | bad_call | inconclusive",
  "confidence": 0.0,
  "primary_rule_id": null,
  "supporting_rule_ids": [],
  "reasoning": "2 to 4 sentences applying available evidence",
  "flags": ["Sport-specific adjudication guidelines for {sport} are not yet configured."]
}}
""".strip()


# ---------------------------------------------------------------------------
# Sport-keyed prompt dicts.
# Keys must match keys in rules.sport_config.SPORTS.
# To implement a new sport: add a named constant above and replace the stub
# call with it here.
# ---------------------------------------------------------------------------

_PERCEPTION_PROMPTS: dict[str, str] = {
    "basketball": _BASKETBALL_PERCEPTION_PROMPT,
    "hockey":     _make_stub_perception_prompt("hockey"),
    "soccer":     _make_stub_perception_prompt("soccer"),
    "lacrosse":   _make_stub_perception_prompt("lacrosse"),
}

_RETRIEVAL_PROMPTS: dict[str, str] = {
    "basketball": _BASKETBALL_RETRIEVAL_PROMPT,
    "hockey":     _make_stub_retrieval_prompt("hockey"),
    "soccer":     _make_stub_retrieval_prompt("soccer"),
    "lacrosse":   _make_stub_retrieval_prompt("lacrosse"),
}

_ADJUDICATOR_PROMPTS: dict[str, str] = {
    "basketball": _BASKETBALL_ADJUDICATOR_PROMPT,
    "hockey":     _make_stub_adjudicator_prompt("hockey"),
    "soccer":     _make_stub_adjudicator_prompt("soccer"),
    "lacrosse":   _make_stub_adjudicator_prompt("lacrosse"),
}


def _get_perception_prompt(sport: str) -> str:
    return _PERCEPTION_PROMPTS.get(sport, _make_stub_perception_prompt(sport))


def _get_retrieval_prompt(sport: str) -> str:
    return _RETRIEVAL_PROMPTS.get(sport, _make_stub_retrieval_prompt(sport))


def _get_adjudicator_prompt(sport: str) -> str:
    return _ADJUDICATOR_PROMPTS.get(sport, _make_stub_adjudicator_prompt(sport))
```

- [ ] **Step 5: Run prompt tests — verify they pass**

```bash
pytest tests/test_sport_routing.py -k "prompt" -v
```

Expected: `9 passed`

- [ ] **Step 6: Run full suite — verify nothing regressed**

```bash
pytest tests/test_sport_routing.py -v
```

Expected: `24 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/services/ai_analyzer.py backend/tests/test_sport_routing.py
git commit -m "feat: add sport-keyed prompt dicts and selector functions; rename basketball constants"
```

---

## Task 3 — Thread sport through pipeline functions

**Files:**
- Modify: `backend/services/ai_analyzer.py`
  - `_rule_records()` — add `sport: str` param, use `get_rules_for_sport()`
  - `_retrieve_rules()` — add `sport: str` param, guard basketball boosters
  - `_perception_agent()` — add `sport: str` param, call `_get_perception_prompt(sport)`
  - `_retrieval_agent()` — add `sport: str` param, call `_get_retrieval_prompt(sport)`
  - `_adjudicator_agent()` — add `sport: str` param, call `_get_adjudicator_prompt(sport)`
  - `_run_four_agent_pipeline()` — pass `sport` to every sub-call
- Modify: `backend/tests/test_sport_routing.py` (append rule routing tests)

- [ ] **Step 1: Append failing rule routing tests**

Add to the bottom of `backend/tests/test_sport_routing.py`:

```python
# ---------------------------------------------------------------------------
# Rule routing
# ---------------------------------------------------------------------------

from services.ai_analyzer import _rule_records, _retrieve_rules

_MINIMAL_PERCEPTION: dict = {
    "event_type": "unclear",
    "summary": "a play",
    "offensive_control_status": "unclear",
    "defender_status": {},
    "court_geometry": {},
}


def test_rule_records_basketball_returns_nine_rules():
    assert len(_rule_records("basketball")) == 9

def test_rule_records_basketball_has_block_charge():
    ids = [r["rule_id"] for r in _rule_records("basketball")]
    assert "BLOCK_CHARGE" in ids

def test_rule_records_hockey_returns_empty_list():
    assert _rule_records("hockey") == []

def test_rule_records_soccer_returns_empty_list():
    assert _rule_records("soccer") == []

def test_rule_records_lacrosse_returns_empty_list():
    assert _rule_records("lacrosse") == []


def test_retrieve_rules_basketball_returns_block_charge_first_for_blocking_query():
    perception = {
        **_MINIMAL_PERCEPTION,
        "event_type": "possible_blocking_foul",
        "summary": "defender slides into path of ball handler",
        "defender_status": {
            "primary_or_secondary": "primary",
            "legal_guarding_position": "not_established",
            "moving_direction": "lateral",
            "inside_restricted_area": False,
        },
        "court_geometry": {"key_zone": "paint_lane"},
    }
    rules = _retrieve_rules("blocking foul legal guarding position established", perception, "basketball")
    assert 1 <= len(rules) <= 5
    assert rules[0]["rule_id"] == "BLOCK_CHARGE"

def test_retrieve_rules_hockey_returns_empty_list():
    rules = _retrieve_rules("hockey slashing high stick", _MINIMAL_PERCEPTION, "hockey")
    assert rules == []

def test_retrieve_rules_basketball_preserves_existing_behavior():
    """Basketball must return the same top result as before the refactor."""
    perception = {
        **_MINIMAL_PERCEPTION,
        "event_type": "possible_blocking_foul",
        "defender_status": {"moving_direction": "lateral", "inside_restricted_area": False},
        "court_geometry": {"key_zone": "restricted_area"},
    }
    rules = _retrieve_rules("blocking charge restricted area secondary defender", perception, "basketball")
    assert len(rules) > 0
    assert rules[0]["rule_id"] in ("BLOCK_CHARGE", "RESTRICTED_AREA")
```

- [ ] **Step 2: Run new tests — verify they fail**

```bash
pytest tests/test_sport_routing.py -k "rule_record or retrieve_rule" -v 2>&1 | head -20
```

Expected: `TypeError: _rule_records() takes 0 positional arguments but 1 was given`

- [ ] **Step 3: Rewrite `_rule_records` to accept `sport`**

Replace the entire function (around line 441):

```python
def _rule_records(sport: str) -> list[dict]:
    from rules.sport_config import get_rules_for_sport
    return [
        {
            "rule_id": key.upper(),
            "section_title": rule["rule_applied"],
            "text": rule["summary"],
            "page_number": rule.get("page_number", 1),
            "call_type": rule["call_type"],
        }
        for key, rule in get_rules_for_sport(sport).items()
    ]
```

- [ ] **Step 4: Rewrite `_retrieve_rules` to accept `sport` and guard basketball boosters**

Replace the entire function (around line 456):

```python
def _retrieve_rules(query: str, perception: dict, sport: str, limit: int = 5) -> list[dict]:
    defender_status = perception.get("defender_status") or {}
    court_geometry = perception.get("court_geometry") or {}
    haystack = (
        f"{query} {perception.get('event_type', '')} {perception.get('summary', '')} "
        f"{perception.get('offensive_control_status', '')} "
        f"{court_geometry.get('key_zone', '')} "
        f"{defender_status.get('primary_or_secondary', '')} "
        f"{defender_status.get('legal_guarding_position', '')} "
        f"{defender_status.get('moving_direction', '')}"
    ).lower()

    scored: list[tuple[int, dict]] = []
    for rule in _rule_records(sport):
        rule_text = (
            f"{rule['rule_id']} {rule['section_title']} {rule['text']} {rule['call_type']}"
        ).lower()
        score = sum(1 for term in haystack.split() if term in rule_text)

        # Basketball-specific keyword boosters — only applied when sport is basketball.
        if sport == "basketball":
            if rule["rule_id"] == "BLOCK_CHARGE" and any(
                t in haystack for t in ["charge", "blocking", "guarding", "lateral", "torso", "established"]
            ):
                score += 6
            if rule["rule_id"] == "RESTRICTED_AREA" and any(
                t in haystack for t in ["restricted", "secondary", "paint", "lane", "basket"]
            ):
                score += 8
            if rule["rule_id"] == "VERTICALITY" and any(
                t in haystack for t in ["vertical", "cylinder", "straight", "landing", "forward"]
            ):
                score += 7
            if rule["rule_id"] == "AIRBORNE_SHOOTER" and any(
                t in haystack for t in ["airborne", "shooter", "upward", "landing", "shooting"]
            ):
                score += 7
            if rule["rule_id"] == "INCIDENTAL_CONTACT" and any(
                t in haystack for t in ["incidental", "rhythm", "speed", "balance", "quickness", "marginal"]
            ):
                score += 7
            if rule["rule_id"] == "SHOOTING_CONTACT" and any(
                t in haystack for t in ["shoot", "shooter", "airborne", "arm", "landing", "verticality"]
            ):
                score += 6
            if rule["rule_id"] == "TRAVEL" and any(
                t in haystack for t in ["travel", "pivot", "gather", "steps", "dribble"]
            ):
                score += 6
            if rule["rule_id"] == "OUT_OF_BOUNDS" and any(
                t in haystack for t in ["out", "boundary", "sideline", "baseline", "last"]
            ):
                score += 6
            if rule["rule_id"] == "GOALTENDING" and any(
                t in haystack for t in ["goaltend", "downward", "cylinder", "rim", "interference"]
            ):
                score += 6

        scored.append((score, rule))

    return [
        rule for _, rule in sorted(scored, key=lambda item: item[0], reverse=True)
    ][:limit]
```

- [ ] **Step 5: Run rule routing tests — verify they pass**

```bash
pytest tests/test_sport_routing.py -k "rule_record or retrieve_rule" -v
```

Expected: `8 passed`

- [ ] **Step 6: Add `sport` param to `_perception_agent`**

Replace the entire function (around line 389):

```python
def _perception_agent(frame_paths: list[Path], original_call: str, sport: str) -> dict:
    context = (
        f"The on-court referee called: '{original_call}'. Use this only as context "
        "for what to focus on. Do not let it bias your perception of what happened."
        if original_call
        else "No original call was provided. Describe what you observe."
    )
    user_blocks = _image_blocks_for_anthropic(frame_paths)
    user_blocks.append(
        {
            "type": "text",
            "text": (
                f"Analyze these {len(frame_paths)} frames from a {sport} clip.\n\n"
                f"{context}\n\nReturn your structured observation as JSON."
            ),
        }
    )
    return _extract_json(
        _call_anthropic_messages(
            system_prompt=_get_perception_prompt(sport),
            user_content=user_blocks,
            temperature=0,
            max_tokens=1600,
        )
    )
```

- [ ] **Step 7: Add `sport` param to `_retrieval_agent`**

Replace the entire function (around line 416):

```python
def _retrieval_agent(perception: dict, sport: str) -> str:
    defender_status = perception.get("defender_status") or {}
    court_geometry = perception.get("court_geometry") or {}
    prompt = f"""
Event type: {perception.get("event_type", "unclear")}
Summary: {perception.get("summary", "")}
Contact detected: {perception.get("contact_detected", False)}
Contact location: {perception.get("contact_location", "unclear")}
Ball state: {perception.get("ball_state", "unclear")}
Offensive control: {perception.get("offensive_control_status", "unclear")}
Court zone: {court_geometry.get("key_zone", "backcourt_or_unclear")}
Restricted area defender: {defender_status.get("inside_restricted_area", "unclear")}
Legal guarding position: {defender_status.get("legal_guarding_position", "unclear")}
Defender movement: {defender_status.get("moving_direction", "unclear")}

Write the rulebook search query.
""".strip()
    return _call_anthropic_messages(
        system_prompt=_get_retrieval_prompt(sport),
        user_content=prompt,
        temperature=0,
        max_tokens=80,
    ).strip().strip('"')
```

- [ ] **Step 8: Add `sport` param to `_adjudicator_agent`**

Replace the entire function signature and the `system_prompt` line (around line 522):

```python
def _adjudicator_agent(
    *,
    perception: dict,
    rules: list[dict],
    original_call: str,
    framing: str,
    temperature: float,
    sport: str,
) -> dict:
    original_call_line = (
        f"'{original_call}'"
        if original_call
        else "(not provided - judge whether the play was correctly officiated assuming the on-court call was made)"
    )
    prompt = f"""
Original call: {original_call_line}

PERCEPTION OUTPUT:
{json.dumps(perception, indent=2)}

RETRIEVED RULES:
{_rules_text(rules)}

Issue your verdict as JSON.
""".strip()
    return _extract_json(
        _call_anthropic_messages(
            system_prompt=f"{_get_adjudicator_prompt(sport)}\n\n{framing}",
            user_content=prompt,
            temperature=temperature,
            max_tokens=1200,
        )
    )
```

- [ ] **Step 9: Update `_run_four_agent_pipeline` to pass `sport` to every sub-call**

The function signature already has `sport: str`. Update only the body where sub-functions are called:

```python
        perception = _perception_agent(frame_paths, original_call, sport)
        retrieval_query = _retrieval_agent(perception, sport)
        retrieved_rules = _retrieve_rules(retrieval_query, perception, sport)
        adjudicator_a = _adjudicator_agent(
            perception=perception,
            rules=retrieved_rules,
            original_call=original_call,
            framing=CONSERVATIVE_FRAMING,
            temperature=0.2,
            sport=sport,
        )
        adjudicator_b = _adjudicator_agent(
            perception=perception,
            rules=retrieved_rules,
            original_call=original_call,
            framing=SKEPTICAL_FRAMING,
            temperature=0.7,
            sport=sport,
        )
```

- [ ] **Step 10: Syntax check**

```bash
python -m compileall services/ai_analyzer.py
```

Expected: `Compiling services/ai_analyzer.py...` with no error lines.

- [ ] **Step 11: Run full test suite**

```bash
pytest tests/test_sport_routing.py -v
```

Expected: `32 passed`

- [ ] **Step 12: Commit**

```bash
git add backend/services/ai_analyzer.py backend/tests/test_sport_routing.py
git commit -m "feat: thread sport param through _perception_agent, _retrieval_agent, _retrieve_rules, _rule_records, _adjudicator_agent, _run_four_agent_pipeline"
```

---

## Task 4 — Fix hardcoded output strings and `analyze_clip` entry point

**Files:**
- Modify: `backend/services/ai_analyzer.py`
  - `_mock_ai_result()` line ~591: `"sport": "basketball"` → `"sport": sport`
  - `_rule_by_id()` line ~753: remove basketball-specific fallback dict
  - `_frontend_perception()` line ~797: add `sport: str` param; use it for `"sport"` field
  - `_build_response()` line ~898: add `sport: str` param; pass it to `_frontend_perception()`
  - `analyze_clip()` line ~970: replace `_clean(sport, "basketball")` with `normalize_sport()`; add `sport=normalized_sport` to `_build_response` call
- Modify: `backend/tests/test_sport_routing.py` (append output field tests)

- [ ] **Step 1: Append failing output field tests**

Add to the bottom of `backend/tests/test_sport_routing.py`:

```python
# ---------------------------------------------------------------------------
# Output sport field correctness
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock
from services.ai_analyzer import _mock_ai_result, _frontend_perception, _rule_by_id


def test_mock_ai_result_sport_field_matches_hockey():
    mock_file = MagicMock()
    result = _mock_ai_result(mock_file, "hockey", "", "", "", "", None, "test fallback")
    assert result["perception"]["sport"] == "hockey"

def test_mock_ai_result_sport_field_matches_basketball():
    mock_file = MagicMock()
    result = _mock_ai_result(mock_file, "basketball", "", "", "", "", None, "test fallback")
    assert result["perception"]["sport"] == "basketball"

def test_mock_ai_result_sport_field_matches_soccer():
    mock_file = MagicMock()
    result = _mock_ai_result(mock_file, "soccer", "", "", "", "", None, "test fallback")
    assert result["perception"]["sport"] == "soccer"


def test_frontend_perception_sport_field_hockey():
    result = _frontend_perception({"event_type": "unclear", "summary": "test"}, "mock", "", "hockey")
    assert result["sport"] == "hockey"

def test_frontend_perception_sport_field_basketball():
    result = _frontend_perception({"event_type": "unclear", "summary": "test"}, "mock", "", "basketball")
    assert result["sport"] == "basketball"


def test_rule_by_id_with_empty_rules_returns_no_rule_placeholder():
    result = _rule_by_id(None, [])
    assert result["rule_id"] == "NO_RULE"

def test_rule_by_id_finds_exact_match():
    rules = [
        {"rule_id": "BLOCK_CHARGE", "section_title": "test", "text": "test", "page_number": 1, "call_type": "Block"},
    ]
    assert _rule_by_id("BLOCK_CHARGE", rules)["rule_id"] == "BLOCK_CHARGE"

def test_rule_by_id_returns_first_rule_when_id_not_found():
    rules = [
        {"rule_id": "BLOCK_CHARGE", "section_title": "test", "text": "test", "page_number": 1, "call_type": "Block"},
    ]
    assert _rule_by_id("NONEXISTENT", rules)["rule_id"] == "BLOCK_CHARGE"
```

- [ ] **Step 2: Run new tests — verify they fail**

```bash
pytest tests/test_sport_routing.py -k "mock_ai or frontend_perception or rule_by_id" -v 2>&1 | head -25
```

Expected: `AssertionError: assert 'basketball' == 'hockey'` (and similar)

- [ ] **Step 3: Fix `_mock_ai_result` — change `"sport": "basketball"` to `"sport": sport`**

Find this line (around line 591):
```python
            "sport": "basketball",
```
Change to:
```python
            "sport": sport,
```

- [ ] **Step 4: Update `_frontend_perception` signature and `"sport"` field**

Change the function signature (around line 797):
```python
def _frontend_perception(perception: dict, provider_used: str, retrieval_query: str, sport: str) -> dict:
```

Change the `"sport"` field in the return dict (was line 799):
```python
        "sport": sport,
```

- [ ] **Step 5: Update `_build_response` to accept and pass `sport`**

Change signature (around line 898):
```python
def _build_response(
    *,
    agent_result: dict,
    clip_id: str,
    frame_paths: list[Path],
    video_metadata: dict | None,
    processing_time_seconds: float,
    sport: str,
) -> dict:
```

Change the `_frontend_perception` call inside `_build_response`:
```python
            "perception": _frontend_perception(perception, provider_used, retrieval_query, sport),
```

- [ ] **Step 6: Fix `_rule_by_id` fallback — remove basketball-specific hardcoding**

Replace the fallback dict (around line 759):
```python
    return rules[0] if rules else {
        "rule_id": "BLOCK_CHARGE",
        "section_title": DEFAULT_BASKETBALL_RULE["rule_applied"],
        "text": DEFAULT_BASKETBALL_RULE["summary"],
        "page_number": 1,
        "call_type": DEFAULT_BASKETBALL_RULE["call_type"],
    }
```
With:
```python
    return rules[0] if rules else {
        "rule_id": "NO_RULE",
        "section_title": "No applicable rule found",
        "text": "No specific rules were retrieved for this play.",
        "page_number": 0,
        "call_type": "Unknown",
        "similarity_score": 0.0,
    }
```

- [ ] **Step 7: Update `analyze_clip` — use `normalize_sport`, pass `sport` to `_build_response`**

At line ~970, replace:
```python
    normalized_sport = _clean(sport, "basketball")
```
With:
```python
    from rules.sport_config import normalize_sport
    normalized_sport = normalize_sport(sport)
```

At the `_build_response` call (~line 989), add `sport=normalized_sport`:
```python
    return _build_response(
        agent_result=agent_result,
        clip_id=clip_id,
        frame_paths=frame_paths,
        video_metadata=video_metadata,
        processing_time_seconds=perf_counter() - start,
        sport=normalized_sport,
    )
```

- [ ] **Step 8: Run full test suite**

```bash
pytest tests/test_sport_routing.py -v
```

Expected: `40 passed`, `0 failed`

- [ ] **Step 9: Syntax check all modified modules**

```bash
python -m compileall services/ rules/
```

Expected: No error lines.

- [ ] **Step 10: Final compile smoke test — import the module**

```bash
python -c "from services.ai_analyzer import analyze_clip; print('import OK')"
```

Expected: `import OK`

- [ ] **Step 11: Commit**

```bash
git add backend/services/ai_analyzer.py backend/tests/test_sport_routing.py
git commit -m "feat: fix hardcoded sport strings in output functions; use normalize_sport in analyze_clip; sport-neutral rule_by_id fallback"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Covered by |
|-------------|-----------|
| `SPORTS = {"basketball": ..., "hockey": ..., "soccer": ..., "lacrosse": ...}` | Task 1 — `sport_config.py` |
| Replace `PERCEPTION_SYSTEM_PROMPT` with sport-keyed dict | Task 2 — `_PERCEPTION_PROMPTS` |
| Replace `RETRIEVAL_SYSTEM_PROMPT` with sport-keyed dict | Task 2 — `_RETRIEVAL_PROMPTS` |
| Replace `ADJUDICATOR_BASE_SYSTEM_PROMPT` with sport-keyed dict | Task 2 — `_ADJUDICATOR_PROMPTS` |
| Thread sport through `_perception_agent` | Task 3 Step 6 |
| Thread sport through `_retrieval_agent` | Task 3 Step 7 |
| Thread sport through `_retrieve_rules` | Task 3 Step 4 |
| Thread sport through `_rule_records` | Task 3 Step 3 |
| Thread sport through `_adjudicator_agent` | Task 3 Step 8 |
| Preserve existing basketball behavior | Tested in Task 3 Step 1 (`test_retrieve_rules_basketball_preserves_existing_behavior`) |
| No hockey/soccer/lacrosse rules yet — routing only | Stubs return empty rules; adjudicator returns inconclusive |

**Placeholder scan:** No TBD, TODO, or "implement later" strings in any code block.

**Type consistency:**
- `_rule_records(sport: str) -> list[dict]` — used consistently in `_retrieve_rules(query, perception, sport, limit)`
- `_frontend_perception(perception, provider_used, retrieval_query, sport)` — caller in `_build_response` updated in Task 4 Step 5
- `_build_response(..., sport: str)` — caller in `analyze_clip` updated in Task 4 Step 7
- `_adjudicator_agent(..., sport: str)` — both call sites in `_run_four_agent_pipeline` updated in Task 3 Step 9
