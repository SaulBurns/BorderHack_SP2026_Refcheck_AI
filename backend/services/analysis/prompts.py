"""Shared prompt catalog: reasoning framings, stub builders, and selectors.

Sport-specific prompt *strings* live in each sport's plugin
(`sports/<sport>/prompts.py`). This module keeps only what is genuinely shared:

- the sport-neutral reasoning framings appended to each adjudicator, and
- the generic stub prompt builders used for sports with no dedicated plugin, and
- the `_get_*_prompt(sport)` selectors the pipeline calls, which now delegate to
  `get_sport(sport).*_prompt()` (the Sport plugin owns its prompts).

Adding a sport therefore never touches this file — its prompts come from its
plugin via the delegation below.
"""

from __future__ import annotations


CONSERVATIVE_FRAMING = """
REASONING POSTURE - CONSERVATIVE:

The on-court referee saw the play live, in full speed, from their position. Give the original call the benefit of the doubt unless the rules and perception evidence clearly indicate otherwise. This does not mean defending bad calls.
""".strip()

SKEPTICAL_FRAMING = """
REASONING POSTURE - SKEPTICAL:

You are an independent reviewer. Do not defer to the original call by default. Examine the evidence and rules on their own merits. If the evidence supports a different interpretation than the original call, say so.
""".strip()


# ---------------------------------------------------------------------------
# Stub prompt builders for sports with no dedicated plugin (GenericSport).
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


def _make_stub_adjudicator_prompt(sport: str) -> str:
    return f"""
You are a {sport} officiating reviewer.

You will be given a structured description of a play and the sport's rulebook.
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
# Selectors — delegate to the Sport plugin (the single source of truth).
# A lazy import avoids the sports<->services import cycle.
# ---------------------------------------------------------------------------

def _get_perception_prompt(sport: str) -> str:
    from sports import get_sport
    return get_sport(sport).perception_prompt()


def _get_adjudicator_prompt(sport: str) -> str:
    from sports import get_sport
    return get_sport(sport).adjudicator_prompt()
