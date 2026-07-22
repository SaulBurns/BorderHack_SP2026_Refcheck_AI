"""Shared prompt catalog: layered composition, framings, stubs, selectors (Sprint 16C).

Every system prompt is composed in three layers — **Common → Sport → Task** —
instead of each sport repeating the shared sections verbatim:

- **Common Instructions** (this module): the sport-neutral fragments every prompt
  shares — the perception intro/visual-quality/output-header/uncertainty/impact-zone
  note, and the adjudicator intro/valid-verdicts/citation/uncertainty/output
  instruction. Defined **once** here.
- **Sport Instructions** (`sports/<sport>/prompts.py`): the sport-specific bodies —
  observation guidelines, geometry, the perception JSON schema body, the decision
  framework, and the rulebook/official names. Each plugin `compose()`s the Common
  fragments with its own bodies.
- **Task Instructions**: the per-agent framing — perception vs. adjudicator (the two
  prompt builders) plus the conservative/skeptical `*_FRAMING` appended per adjudicator.

`compose(*parts)` joins the layers. `_get_*_prompt(sport)` still delegates to the
Sport plugin, so adding a sport never touches this file.
"""

from __future__ import annotations


def compose(*parts: str) -> str:
    """Join prompt fragments into one prompt (strip each, drop empties, blank-line sep)."""
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


# ---------------------------------------------------------------------------
# Task layer — reasoning postures appended to each adjudicator (per-agent).
# ---------------------------------------------------------------------------

CONSERVATIVE_FRAMING = """
REASONING POSTURE - CONSERVATIVE:

The on-court referee saw the play live, in full speed, from their position. Give the original call the benefit of the doubt unless the rules and perception evidence clearly indicate otherwise. This does not mean defending bad calls.
""".strip()

SKEPTICAL_FRAMING = """
REASONING POSTURE - SKEPTICAL:

You are an independent reviewer. Do not defer to the original call by default. Examine the evidence and rules on their own merits. If the evidence supports a different interpretation than the original call, say so.
""".strip()


# ---------------------------------------------------------------------------
# Common layer — perception fragments (shared by every sport's perception prompt).
# ---------------------------------------------------------------------------

def perception_intro(specialty: str, clip_noun: str) -> str:
    """Opening role + task, shared by every perception prompt.

    `specialty` names the sport for the analyst role (e.g. "ice hockey"); `clip_noun`
    names the clip (e.g. "hockey"). Everything after those two words is identical
    across sports.
    """
    return (
        f"You are a sports video analyst specializing in {specialty} officiating review.\n\n"
        f"You will receive a sequence of evenly-spaced frames from a short {clip_noun} clip. "
        "Your job is to describe what you observe in structured form. You are NOT issuing a "
        "verdict. A separate agent will rule on the call. Your role is to be the most accurate "
        "possible eyes for the system."
    )


PERCEPTION_VISUAL_QUALITY = (
    "Visual quality: Honestly assess the camera angle. Is the key moment clearly visible, "
    "partially obscured, blocked by another player, or unusable?"
)


def perception_uncertainty(tail: str = "") -> str:
    """UNCERTAINTY DISCIPLINE for perception; `tail` adds sport-specific angle notes."""
    base = (
        "UNCERTAINTY DISCIPLINE:\n"
        "Be honest. If a frame is blurry, an angle is wrong, or you cannot tell what happened, "
        "say so and lower perception_confidence."
    )
    return f"{base} {tail.strip()}" if tail.strip() else base


PERCEPTION_OUTPUT_HEADER = "OUTPUT FORMAT:\nOutput ONLY valid JSON. No prose, no markdown fences."


def impact_zone_note(uses: str) -> str:
    """Trailing impact-zone note; `uses` is the sport-specific list of what to mark."""
    return (
        "Impact zone should be normalized to the frame: x_percent and y_percent range from 0 to "
        f"100. Use it to {uses}. If the exact point is unclear, estimate the most relevant area "
        "and lower confidence."
    )


# ---------------------------------------------------------------------------
# Common layer — adjudicator fragments (shared by every sport's adjudicator prompt).
# ---------------------------------------------------------------------------

def adjudicator_intro(rulebook_line: str, official: str) -> str:
    """The 'You will be given: 1/2/3 … issue a verdict' intro, shared by every sport.

    `rulebook_line` names the sport's rulebook (item 2); `official` names the on-field
    official (e.g. "on-ice official").
    """
    return (
        "You will be given:\n"
        "1. A structured description of what happened in a clip, produced by a perception agent\n"
        f"2. {rulebook_line}\n"
        f"3. Optionally, what the {official} originally called\n\n"
        "Your job is to issue a verdict on whether the original officiating call was correct."
    )


VALID_VERDICTS = (
    "VALID VERDICTS:\n"
    '- "fair_call": the original call was consistent with the rules, given the evidence\n'
    '- "bad_call": the original call was inconsistent with the rules, given the evidence\n'
    '- "inconclusive": the visual evidence is insufficient to render a confident verdict'
)

CITATION_DISCIPLINE = (
    "CITATION DISCIPLINE:\n"
    "You must cite at least one rule by its rule_id from the provided rules. Do not invent rule "
    "IDs. Your reasoning must explicitly connect the play details to the cited rule text."
)


def adjudicator_uncertainty(tail: str = "") -> str:
    """UNCERTAINTY DISCIPLINE for adjudication; `tail` adds sport-specific angle notes."""
    base = (
        "UNCERTAINTY DISCIPLINE:\n"
        'If perception_confidence is low (<0.5) or visual_quality is "obstructed" or "poor", '
        "lean toward inconclusive."
    )
    return f"{base} {tail.strip()}" if tail.strip() else base


# The concise replacement for the former inline verdict-JSON block. Post-Sprint-16B
# the reply is validated against `AdjudicatorResponse` and the schema is passed to the
# provider, so the verbose JSON example is redundant — this one line names every field
# with just enough semantics, shorter than the block it replaces. Identical across every
# sport (the dedup guarantee).
ADJUDICATOR_OUTPUT_INSTRUCTION = (
    "OUTPUT FORMAT:\n"
    "Return ONLY valid JSON with keys: verdict (fair_call | bad_call | inconclusive), "
    "confidence (0.0-1.0), primary_rule_id (a provided rule_id or null), supporting_rule_ids, "
    "reasoning (2-4 sentences citing the primary rule), flags. No prose, no markdown fences."
)


# ---------------------------------------------------------------------------
# Stub prompt builders for sports with no dedicated plugin (GenericSport).
# They compose the shared fragments too, with generic bodies — so the fallback
# stays consistent with the real sports and shares the Common layer.
# ---------------------------------------------------------------------------

_STUB_PERCEPTION_JSON = """
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


def _make_stub_perception_prompt(sport: str) -> str:
    return compose(
        perception_intro(sport, sport),
        "OBSERVATION GUIDELINES:\n"
        "Describe the players involved, their positions, any contact, and the key moment of the "
        "play.",
        PERCEPTION_VISUAL_QUALITY,
        perception_uncertainty(),
        PERCEPTION_OUTPUT_HEADER,
        _STUB_PERCEPTION_JSON.format(sport=sport),
    )


def _make_stub_adjudicator_prompt(sport: str) -> str:
    return compose(
        f"You are a {sport} officiating reviewer.",
        "You will be given a structured description of a play and the sport's rulebook. Issue a "
        "verdict on whether the original call was correct.",
        VALID_VERDICTS,
        "UNCERTAINTY DISCIPLINE:\n"
        "If no rules are provided, return inconclusive with a flag noting the absence of rules. "
        "If perception_confidence is below 0.5, lean toward inconclusive.",
        ADJUDICATOR_OUTPUT_INSTRUCTION,
    )


# ---------------------------------------------------------------------------
# Selectors — delegate to the Sport plugin (the single source of truth).
# A lazy import avoids the sports<->services import cycle.
# ---------------------------------------------------------------------------

def _get_perception_prompt(sport: str) -> str:
    from sports import get_sport
    return get_sport(sport).perception_prompt()


def _get_adjudicator_prompt(sport: str) -> str:
    from sports import get_sport
    return get_sport(sport).adjudicator_prompt()
