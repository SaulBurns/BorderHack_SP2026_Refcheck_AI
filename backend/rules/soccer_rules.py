"""Soccer rulebook corpus (Sprint 10 — first new sport).

Rule records for association football (soccer), mirroring the shape of
``rules/basketball_rules.py``: each entry has a ``call_type``, ``rule_applied``,
and ``summary``. Keys are lowercase and become the uppercase ``rule_id`` used by
adjudication citations and the demo/eval datasets. The full corpus is injected
into the adjudicators (Sprint 16A removed the retrieval stage).

Coverage is scoped to the Sprint 10 supported events: foul, offside, handball,
penalty, red card, yellow card, and goal. Summaries paraphrase the IFAB Laws of
the Game (Laws 10, 11, 12, 14) in plain, reviewer-facing language — they are a
reviewer corpus, not a legal citation.
"""

SOCCER_RULES = {
    "foul": {
        "call_type": "Foul",
        "rule_applied": "Law 12 — Fouls and misconduct (careless, reckless, excessive force)",
        "summary": (
            "A direct free kick is awarded when a player commits a foul such as "
            "kicking, tripping, pushing, holding, or charging an opponent in a manner "
            "the referee considers careless, reckless, or using excessive force. "
            "Contact that is careless is a foul; reckless play warrants a caution; "
            "excessive force warrants a sending-off."
        ),
    },
    "offside": {
        "call_type": "Offside",
        "rule_applied": "Law 11 — Offside position and offence",
        "summary": (
            "An attacker is in an offside position if any part of the head, body, or "
            "feet is nearer the opponents' goal line than both the ball and the "
            "second-to-last defender at the moment the ball is played by a teammate. "
            "Being in an offside position is only an offence if the player becomes "
            "involved in active play by interfering with play, an opponent, or gaining "
            "an advantage. Level with the second-to-last defender is onside."
        ),
    },
    "handball": {
        "call_type": "Handball",
        "rule_applied": "Law 12 — Handling the ball (deliberate contact / unnatural silhouette)",
        "summary": (
            "It is an offence for a player to deliberately touch the ball with the hand "
            "or arm, or to score or create a goal-scoring opportunity after the ball "
            "touches the hand/arm. Handball is judged by whether the arm makes the body "
            "unnaturally bigger or is above the shoulder; accidental contact that does "
            "not gain an advantage is generally not an offence."
        ),
    },
    "penalty": {
        "call_type": "Penalty Kick",
        "rule_applied": "Law 14 — Penalty kick (foul inside the penalty area)",
        "summary": (
            "A penalty kick is awarded when a player commits a direct-free-kick offence "
            "against an opponent inside their own penalty area, or handles the ball there, "
            "while the ball is in play. The location of the offence — not where contact "
            "ends or the players fall — determines whether it is inside the area."
        ),
    },
    "red_card": {
        "call_type": "Red Card",
        "rule_applied": "Law 12 — Sending-off offences (serious foul play / DOGSO / violent conduct)",
        "summary": (
            "A player is sent off for serious foul play, violent conduct, spitting, "
            "denying an obvious goal-scoring opportunity by a handball, denying an "
            "obvious goal-scoring opportunity by a foul (DOGSO), offensive language, or a "
            "second caution. Serious foul play is a challenge that endangers an opponent's "
            "safety or uses excessive force while contesting the ball."
        ),
    },
    "yellow_card": {
        "call_type": "Yellow Card",
        "rule_applied": "Law 12 — Cautionable offences (reckless challenge / unsporting behaviour)",
        "summary": (
            "A player is cautioned for unsporting behaviour, including a reckless "
            "challenge, a tactical foul that stops a promising attack, simulation "
            "(diving), persistent infringement, dissent, or delaying the restart. "
            "Reckless means acting with disregard for the danger to an opponent, short "
            "of the excessive force that requires a sending-off."
        ),
    },
    "goal": {
        "call_type": "Goal",
        "rule_applied": "Law 10 — Determining the outcome of a match (whole of the ball over the line)",
        "summary": (
            "A goal is scored when the whole of the ball passes over the goal line, "
            "between the goalposts and under the crossbar, provided no offence (such as "
            "a handball, foul, or offside) was committed by the scoring team beforehand. "
            "If any part of the ball remains on or above the line, no goal is awarded."
        ),
    },
}
