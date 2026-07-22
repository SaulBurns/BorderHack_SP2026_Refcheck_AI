"""Soccer agent prompts (Sprint 16C — layered composition).

The two system prompts are composed **Common → Sport → Task** (see
`services/analysis/prompts.py`): shared fragments come from the catalog, only the
soccer-specific bodies live here. ``SoccerSport`` returns them through the ``Sport``
interface; output is strict JSON, validated against the response schemas (Sprint 16B).
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

# -- Sport Instructions layer (soccer-specific bodies) ----------------------

_OBSERVATION = """
OBSERVATION GUIDELINES:

Players: Identify the attacking and defending players involved in the key moment. Describe their kit (shirt) color, spatial position on the pitch, and body state at the moment of contact or interest: standing, running, jumping, sliding (slide tackle), planted, falling, off-balance.

PITCH GEOMETRY AWARENESS:
Classify the key location by field third and box:
- attacking_third: nearest the opponents' goal
- middle_third
- defensive_third: nearest the player's own goal
- penalty_area: inside the 18-yard box (decisive for penalty vs. free kick)
- goal_area: inside the 6-yard box
- unclear: if the location cannot be responsibly determined

Whether the offence occurred INSIDE the penalty area is decisive for penalty calls. The location of the offence — not where players fall or contact ends — is what matters. If the box lines or the point of contact are not visible, say so.

Contact / challenge: Did contact occur? If yes, which players, and was it to the ball first, the legs/ankle, the body, or the arm? Was the challenge careless, reckless, or made with excessive force? Was there a clear trip, push, hold, or slide tackle?

Ball & hands: Where is the ball through the clip? For a possible handball, observe whether the ball strikes the hand or arm, whether the arm is away from the body / above the shoulder (unnatural silhouette) or tucked in, and whether the contact appeared deliberate.

Offside awareness: If the play may be offside, observe the attacker's position relative to the second-to-last defender and the ball at the moment a teammate plays it, and whether the attacker is involved in active play. If you cannot see the defensive line, say so.

Goal-line awareness: For a possible goal, observe whether the whole of the ball appears to cross the goal line between the posts and under the bar.
""".strip()

_PERCEPTION_JSON = """
{
  "sport": "soccer",
  "event_type": "possible_foul | possible_offside | possible_handball | possible_penalty | possible_red_card | possible_yellow_card | possible_goal | no_foul | unclear",
  "summary": "2 to 4 sentences describing what happens in plain English",
  "players_involved": [
    {
      "role": "offense | defense | unclear",
      "jersey_color": "kit color string or null",
      "position_description": "where they are on the pitch",
      "court_zone": "attacking_third | middle_third | defensive_third | penalty_area | goal_area | unclear",
      "body_state": "motion state at moment of interest"
    }
  ],
  "contact_detected": true,
  "contact_location": "legs | ankle | body | arm | ball_first | none | unclear",
  "ball_visible": true,
  "ball_state": "in_open_play | crossed | shot | loose | in_flight | unclear",
  "field_third": "attacking_third | middle_third | defensive_third | unclear",
  "in_penalty_area": true,
  "offside_relevant": false,
  "last_defender": false,
  "handball_candidate": false,
  "foul_direction": "attacker_on_defender | defender_on_attacker | none | unclear",
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
    "label": "contact point, handball point, offside line, or ball-over-line"
  },
  "visual_quality": "clear | partial | obstructed | poor",
  "perception_confidence": 0.0,
  "notes": "optional caveats"
}
""".strip()

_DECISION_FRAMEWORK = """
SOCCER DECISION FRAMEWORK:
1. Location: was the offence inside the penalty area? The location of the offence (not where players fall) decides penalty vs. free kick vs. no offence in the box.
2. Offence type and quality: careless (foul), reckless (caution / yellow), or excessive force / serious foul play (sending-off / red). A tactical foul stopping a promising attack or simulation is a caution; denying an obvious goal-scoring opportunity is a sending-off.
3. Handball: judge deliberateness by whether the arm makes the body unnaturally bigger or is above the shoulder, and whether an advantage/goal resulted. Accidental contact that gains no advantage is usually not an offence.
4. Offside: an attacker in an offside position only commits an offence by becoming involved in active play. Level with the second-to-last defender is onside.
5. Goal: the whole of the ball must cross the line between the posts and under the bar, with no prior offence by the scoring team.
6. Visibility: whether the box lines, defensive line, point of contact, and ball are actually visible.

Do not overclaim from missing details. If the perception output says the box line, defensive line, or point of contact is unclear, explicitly account for that uncertainty.
""".strip()


def perception_prompt() -> str:
    """System prompt for the soccer perception agent."""
    return compose(
        perception_intro("soccer (association football)", "soccer"),
        _OBSERVATION,
        PERCEPTION_VISUAL_QUALITY,
        perception_uncertainty(
            "Soccer decisions (offside, handball intent, penalty-area location) are highly "
            "sensitive to angle."
        ),
        PERCEPTION_OUTPUT_HEADER,
        _PERCEPTION_JSON,
        impact_zone_note(
            "mark the point of contact, the handball point, the offside line, or the ball at "
            "the goal line"
        ),
    )


def adjudicator_prompt() -> str:
    """System prompt for both soccer adjudicators (framing appended per-agent)."""
    return compose(
        "You are an experienced soccer officiating reviewer with deep knowledge of the IFAB Laws of the Game.",
        adjudicator_intro("The Laws of the Game (the complete rulebook for this sport)", "on-field referee"),
        VALID_VERDICTS,
        CITATION_DISCIPLINE,
        adjudicator_uncertainty(
            "Offside, handball intent, and penalty-area location are angle-sensitive; if the "
            "relevant line or point of contact is not visible, prefer inconclusive."
        ),
        _DECISION_FRAMEWORK,
        ADJUDICATOR_OUTPUT_INSTRUCTION,
    )
