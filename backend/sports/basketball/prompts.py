"""Basketball agent prompts (Sprint 16C — layered composition).

The two system prompts are composed **Common → Sport → Task** (see
`services/analysis/prompts.py`): the shared fragments (perception intro, visual
quality, output header, verdict fields, citation/uncertainty discipline) come from
the catalog; only the basketball-specific bodies below live here. Output is strict
JSON, validated against the response schemas (Sprint 16B).
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

# -- Sport Instructions layer (basketball-specific bodies) ------------------

_OBSERVATION = """
OBSERVATION GUIDELINES:

Players: Identify offensive and defensive players involved in the key moment. Describe their jersey color, spatial position on the court, and body state at the moment of contact or interest. Body state is critical: stationary, moving laterally, jumping, descending, falling, airborne, planted, sliding.

COURT GEOMETRY AWARENESS:
When describing positions, classify the key players by court zone:
- restricted_area: the painted half-circle directly under the basket
- paint_lane: the larger painted rectangle
- perimeter: outside the paint, inside the three-point line
- beyond_arc: outside the three-point line
- backcourt_or_unclear: if the court position cannot be responsibly determined

The restricted area is decisive for many block/charge calls. A secondary defender generally cannot establish legal guarding position inside the restricted area against a player in control of the ball or in the act of shooting. If the restricted-area arc or the defender's feet are not visible, say so.

Contact: Did contact occur? If yes, which players, and was it at the torso, arm, lower body, or unclear? Was the contact incidental or significant?

Ball: Where is the ball through the clip? Is the offensive player dribbling, gathering, in upward shooting motion, releasing, or is the ball in flight? If the gather or upward motion is unclear, say unclear.

DEFENDER LEGALITY CHECKLIST:
For block/charge or shooting-contact plays, explicitly observe:
- whether the defender is primary or secondary
- whether both feet appear established before upward motion/contact
- whether the defender is moving laterally, backward, forward, or vertically
- whether the defender is inside the restricted area
- whether the offensive player is airborne or in control of the ball
- whether contact affects rhythm, speed, balance, or quickness
""".strip()

_PERCEPTION_JSON = """
{
  "sport": "basketball",
  "event_type": "possible_blocking_foul | possible_charge | possible_travel | possible_goaltending | possible_offensive_foul | out_of_bounds | shot_clock_violation | three_seconds_violation | unclear",
  "summary": "2 to 4 sentences describing what happens in plain English",
  "players_involved": [
    {
      "role": "offense | defense | unclear",
      "jersey_color": "color string or null",
      "position_description": "where they are on the court",
      "court_zone": "restricted_area | paint_lane | perimeter | beyond_arc | backcourt_or_unclear",
      "body_state": "motion state at moment of interest"
    }
  ],
  "contact_detected": true,
  "contact_location": "torso | arm | lower_body | unclear | none",
  "ball_visible": true,
  "ball_state": "gathered | dribbling | upward_motion | released | in_flight | unclear",
  "offensive_control_status": "dribbling | gathered | airborne_shooter | passing | loose_ball | unclear",
  "defender_status": {
    "primary_or_secondary": "primary | secondary | unclear",
    "legal_guarding_position": "established | not_established | unclear",
    "feet_set_before_contact": true,
    "moving_direction": "stationary | lateral | forward | backward | vertical | unclear",
    "inside_restricted_area": true
  },
  "court_geometry": {
    "key_zone": "restricted_area | paint_lane | perimeter | beyond_arc | backcourt_or_unclear",
    "restricted_area_arc_visible": true,
    "defender_feet_visible": true,
    "basket_visible": true
  },
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
    "label": "contact point or decisive action"
  },
  "visual_quality": "clear | partial | obstructed | poor",
  "perception_confidence": 0.0,
  "notes": "optional caveats"
}
""".strip()

_DECISION_FRAMEWORK = """
BASKETBALL DECISION FRAMEWORK:
For block/charge and shooting-contact plays, reason in this order:
1. Court geometry: restricted area, paint/lane, perimeter, or beyond arc. If a secondary defender is inside the restricted area against a player in control or in shooting motion, that strongly affects the ruling.
2. Timing: whether legal guarding position was established before the gather/upward motion/contact.
3. Movement: whether the defender maintained legal verticality or moved into the opponent's path/landing space.
4. Contact effect: whether contact affected rhythm, speed, balance, quickness, shot, or landing.
5. Visibility: whether feet, contact point, ball state, and restricted-area arc are actually visible.

Do not overclaim from missing details. If the perception output says the defender's feet, restricted-area line, or ball state is unclear, explicitly account for that uncertainty.
""".strip()


def perception_prompt() -> str:
    """System prompt for the basketball perception agent."""
    return compose(
        perception_intro("basketball", "basketball"),
        _OBSERVATION,
        PERCEPTION_VISUAL_QUALITY,
        perception_uncertainty(),
        PERCEPTION_OUTPUT_HEADER,
        _PERCEPTION_JSON,
        impact_zone_note(
            "identify the visible contact point, foot placement, ball release, boundary touch, "
            "or other decisive visual region"
        ),
    )


def adjudicator_prompt() -> str:
    """System prompt for both basketball adjudicators (framing appended per-agent)."""
    return compose(
        "You are an experienced basketball officiating reviewer with deep knowledge of the NBA rulebook.",
        adjudicator_intro("The NBA rulebook (the complete rule set for this sport)", "on-court referee"),
        VALID_VERDICTS,
        CITATION_DISCIPLINE,
        adjudicator_uncertainty(
            "If the provided rules do not cover the situation, return inconclusive with a flag."
        ),
        _DECISION_FRAMEWORK,
        ADJUDICATOR_OUTPUT_INSTRUCTION,
    )
