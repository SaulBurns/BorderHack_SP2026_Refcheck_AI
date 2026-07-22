"""Lacrosse agent prompts (Sprint 16C — layered composition).

The two system prompts are composed **Common → Sport → Task** (see
`services/analysis/prompts.py`): shared fragments come from the catalog, only the
lacrosse-specific bodies live here. Output is strict JSON, validated against the
response schemas (Sprint 16B).
"""

from __future__ import annotations

from services.analysis.prompts import (
    ADJUDICATOR_OUTPUT_INSTRUCTION,
    CITATION_DISCIPLINE,
    PERCEPTION_OUTPUT_HEADER,
    PERCEPTION_VISUAL_QUALITY,
    VALID_VERDICTS,
    adjudicator_intro,
    adjudicator_uncertainty,
    compose,
    impact_zone_note,
    perception_intro,
    perception_uncertainty,
)

# -- Sport Instructions layer (lacrosse-specific bodies) --------------------

_OBSERVATION = """
OBSERVATION GUIDELINES:

Players: Identify the attacking and defending players involved in the key moment. Describe their jersey color, spatial position on the field, and body state at the moment of contact or interest: running, dodging, stationary, checking, shooting, falling, defenseless, unaware.

FIELD GEOMETRY AWARENESS:
Classify the key location by area:
- attacking_half: the offensive half past the midline
- defensive_half: the team's own half
- crease: the circle around the goal (an attacking player may not enter it)
- midline: the center line (decisive for offside — required players per half)
- behind_goal: the X area behind the cage
- unclear: if the location cannot be responsibly determined

The CREASE is decisive for crease violations (an attacking player entering the crease, or diving and landing in it, nullifies a goal). The MIDLINE is decisive for offside (a team must keep the required number of players on each side). If the crease line or midline is not visible, say so.

Stick and contact / infraction: Did an infraction occur? Observe the crosse — was there a controlled stick check on the gloves/crosse to dislodge the ball, or an uncontrolled/forceful swing to the body or head (slash)? For a body check, observe whether the opponent had possession or was within five yards of a loose ball, whether the hit came from the front/side vs. behind, and whether it targeted the head or a defenseless player. For pushing, observe whether pressure was applied to the back and whether the opponent had possession.

Ball awareness: Where is the ball through the clip? Note whether a player is carrying it in the crosse, whether it is a loose ball (and which players are within five yards), a shot, or a pass. Loose-ball status changes what contact is legal.

Goalie/crease awareness: Note whether the play involves the goalkeeper or crease.
""".strip()

_PERCEPTION_JSON = """
{
  "sport": "lacrosse",
  "event_type": "possible_illegal_body_check | possible_slash | possible_push | possible_crease_violation | possible_offside | possible_loose_ball_push | no_infraction | unclear",
  "summary": "2 to 4 sentences describing what happens in plain English",
  "players_involved": [
    {
      "role": "offense | defense | unclear",
      "jersey_color": "color string or null",
      "position_description": "where they are on the field",
      "court_zone": "attacking_half | defensive_half | crease | midline | behind_goal | unclear",
      "body_state": "motion state at moment of interest"
    }
  ],
  "contact_detected": true,
  "contact_location": "crosse | gloves | body | back | head | none | unclear",
  "ball_visible": true,
  "ball_state": "carried | loose | shot | passed | unclear",
  "field_area": "attacking_half | defensive_half | crease | midline | behind_goal | unclear",
  "crease_violation": false,
  "cross_check": false,
  "slashing": false,
  "ball_carrier_status": "in_possession | loose_ball | not_in_possession | unclear",
  "warding": false,
  "infraction_candidate": "illegal_body_check | slash | push | crease_violation | offside | loose_ball_push | none | unclear",
  "frame_observations": [
    {
      "frame_index": 1,
      "approx_time_seconds": 0.0,
      "observation": "short concrete observation"
    }
  ],
  "moment_of_interest_seconds": 0.0,
  "impact_zone": {
    "x_percent": 50,
    "y_percent": 50,
    "radius_percent": 12,
    "label": "contact point, stick check, crease, or midline"
  },
  "visual_quality": "clear | partial | obstructed | poor",
  "perception_confidence": 0.0,
  "notes": "optional caveats"
}
""".strip()

_DECISION_FRAMEWORK = """
LACROSSE DECISION FRAMEWORK:
1. Ball/possession context: legal contact depends on it. A body check or push is legal only against a player in possession or within five yards of a loose ball, from the front or side. Contact on a defenseless player, from behind, above the shoulders, or below the waist is illegal.
2. Stick fouls: distinguish a controlled stick check on the gloves/crosse (legal) from a forceful or one-handed swing to the body/head (slashing, a personal foul).
3. Crease: an attacking player entering the crease, or diving and landing in it as the ball crosses, nullifies a goal; contact with a goalkeeper in possession in the crease is a violation.
4. Offside: judge whether the team kept the required number of players on each side of the midline.
5. Severity: personal fouls (illegal body check, slashing) carry time-serving penalties that escalate with severity; technical fouls (pushing, crease, offside, loose-ball push) turn the ball over or nullify a goal.
6. Visibility: whether the crease line, midline, stick contact, and ball status are actually visible.

Do not overclaim from missing details. If the perception output says the crease line, the midline, or the point of contact is unclear, explicitly account for that uncertainty.
""".strip()


def perception_prompt() -> str:
    """System prompt for the lacrosse perception agent."""
    return compose(
        perception_intro("men's field lacrosse", "lacrosse"),
        _OBSERVATION,
        PERCEPTION_VISUAL_QUALITY,
        perception_uncertainty(
            "Lacrosse checks and crease/offside calls are fast and angle-sensitive."
        ),
        PERCEPTION_OUTPUT_HEADER,
        _PERCEPTION_JSON,
        impact_zone_note(
            "mark the point of contact, the stick check, the crease line, or the midline"
        ),
    )


def adjudicator_prompt() -> str:
    """System prompt for both lacrosse adjudicators (framing appended per-agent)."""
    return compose(
        "You are an experienced men's field lacrosse officiating reviewer with deep knowledge of the NCAA lacrosse rulebook.",
        adjudicator_intro("The NCAA lacrosse rulebook (the complete rule set for this sport)", "on-field official"),
        VALID_VERDICTS,
        CITATION_DISCIPLINE,
        adjudicator_uncertainty(
            "Body checks, crease entries, and offside are fast and angle-sensitive; if the "
            "crease line, the midline, or the point of contact is not visible, prefer inconclusive."
        ),
        _DECISION_FRAMEWORK,
        ADJUDICATOR_OUTPUT_INSTRUCTION,
    )
