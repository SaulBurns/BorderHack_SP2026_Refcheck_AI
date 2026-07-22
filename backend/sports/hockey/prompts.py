"""Hockey agent prompts (Sprint 16C — layered composition).

The two system prompts are composed **Common → Sport → Task** (see
`services/analysis/prompts.py`): shared fragments come from the catalog, only the
hockey-specific bodies live here. Output is strict JSON, validated against the
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

# -- Sport Instructions layer (hockey-specific bodies) ----------------------

_OBSERVATION = """
OBSERVATION GUIDELINES:

Players: Identify the attacking and defending players involved in the key moment. Describe their sweater (jersey) color, spatial position on the ice, and body state at the moment of contact or interest: skating, gliding, stationary, checking, falling, off-balance, turned toward the boards.

RINK GEOMETRY AWARENESS:
Classify the key location by zone relative to the blue lines and red line:
- offensive_zone: beyond the attacking blue line
- neutral_zone: between the two blue lines
- defensive_zone: behind the defending blue line
- along_boards: play against the perimeter boards
- near_crease: around the goal crease
- unclear: if the location cannot be responsibly determined

The BLUE LINES are decisive for offside (a player is offside if both skates cross the attacking blue line before the puck — judged by the skates, not the stick). The CENTER RED LINE and the goal line are decisive for icing. If the relevant line or the puck is not visible, say so.

Stick and contact / infraction: Did an infraction occur? Observe the stick's use — was contact made with the stick blade or shaft (hooking, slashing, cross-checking, tripping), or was it a clean check? For a possible boarding, observe whether the checked player was defenseless or turned toward the boards and the violence of the impact. Distinguish a legal poke-check on the puck from a stick infraction on the body.

Puck awareness: Where is the puck through the clip? For icing/offside observe the puck's position relative to the lines and whether it was touched. For stick fouls observe whether the defender played the puck first or the opponent's body.

Goalie awareness: Note whether the goaltender is involved in the play (crease contact, save, or a scramble).
""".strip()

_PERCEPTION_JSON = """
{
  "sport": "hockey",
  "event_type": "possible_icing | possible_offside | possible_tripping | possible_cross_checking | possible_boarding | possible_slashing | possible_hooking | no_infraction | unclear",
  "summary": "2 to 4 sentences describing what happens in plain English",
  "players_involved": [
    {
      "role": "offense | defense | unclear",
      "jersey_color": "sweater color string or null",
      "position_description": "where they are on the ice",
      "court_zone": "offensive_zone | neutral_zone | defensive_zone | along_boards | near_crease | unclear",
      "body_state": "motion state at moment of interest"
    }
  ],
  "contact_detected": true,
  "contact_location": "stick_blade | stick_shaft | body | boards | skates | none | unclear",
  "ball_visible": true,
  "ball_state": "carried | passed | shot | loose | dumped_in | unclear",
  "zone": "offensive_zone | neutral_zone | defensive_zone | along_boards | near_crease | unclear",
  "goalie_involved": false,
  "puck_possession": "attacker | defender | contested | loose | unclear",
  "infraction_candidate": "icing | offside | tripping | cross_checking | boarding | slashing | hooking | none | unclear",
  "boards_involved": false,
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
    "label": "contact point, stick infraction, blue line, or puck at the goal line"
  },
  "visual_quality": "clear | partial | obstructed | poor",
  "perception_confidence": 0.0,
  "notes": "optional caveats"
}
""".strip()

_DECISION_FRAMEWORK = """
HOCKEY DECISION FRAMEWORK:
1. Line calls: for offside, judge whether both skates crossed the attacking blue line before the puck (skates, not the stick; straddling the line is onside). For icing, judge whether the puck was shot from behind the center red line across the goal line untouched, and whether an exception applies (short-handed, through the crease, or a defender could have played it).
2. Stick fouls: distinguish a legal poke-check that plays the puck first from tripping/hooking/slashing/cross-checking on the body. Hooking restrains or impedes; slashing is a swing/chop; cross-checking uses both hands with the stick off the ice; tripping causes a fall with stick/leg/foot.
3. Boarding: judge the violence of the check and whether the opponent was defenseless or turned toward the boards — the onus is on the checker.
4. Severity: whether the infraction warrants a minor, a major, or a game misconduct (notably when injury results).
5. Visibility: whether the blue line, red line, goal line, stick contact, and puck are actually visible.

Do not overclaim from missing details. If the perception output says the line, the puck, or the point of stick contact is unclear, explicitly account for that uncertainty.
""".strip()


def perception_prompt() -> str:
    """System prompt for the hockey perception agent."""
    return compose(
        perception_intro("ice hockey", "hockey"),
        _OBSERVATION,
        PERCEPTION_VISUAL_QUALITY,
        perception_uncertainty(
            "Hockey line calls (offside, icing) and stick fouls are highly sensitive to angle "
            "and speed."
        ),
        PERCEPTION_OUTPUT_HEADER,
        _PERCEPTION_JSON,
        impact_zone_note(
            "mark the point of contact, the stick infraction, the blue line for offside, or the "
            "puck at the goal line for icing"
        ),
    )


def adjudicator_prompt() -> str:
    """System prompt for both hockey adjudicators (framing appended per-agent)."""
    return compose(
        "You are an experienced ice hockey officiating reviewer with deep knowledge of the NHL rulebook.",
        adjudicator_intro("The NHL rulebook (the complete rule set for this sport)", "on-ice official"),
        VALID_VERDICTS,
        CITATION_DISCIPLINE,
        adjudicator_uncertainty(
            "Offside, icing, and stick fouls are angle- and speed-sensitive; if the relevant "
            "line, the puck, or the stick contact is not visible, prefer inconclusive."
        ),
        _DECISION_FRAMEWORK,
        ADJUDICATOR_OUTPUT_INSTRUCTION,
    )
