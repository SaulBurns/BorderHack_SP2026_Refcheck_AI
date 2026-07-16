"""Lacrosse rulebook corpus (Sprint 12 — fourth sport).

Keyword-retrievable rule records for men's field lacrosse, mirroring the shape of
``rules/basketball_rules.py``, ``rules/soccer_rules.py``, and
``rules/hockey_rules.py``: each entry has a ``call_type``, ``rule_applied``, and
``summary``. Keys are lowercase and become the uppercase ``rule_id`` used by
retrieval, adjudication citations, and the demo/eval datasets.

Coverage is scoped to the Sprint 12 supported events: illegal body check, slash,
push, crease violation, offside, and loose-ball push. Summaries paraphrase the
NCAA men's lacrosse rulebook in plain, reviewer-facing language — they are a
retrieval corpus, not a legal citation.
"""

LACROSSE_RULES = {
    "illegal_body_check": {
        "call_type": "Illegal Body Check",
        "rule_applied": "Rule 5, Section 3 — Illegal body checking (personal foul)",
        "summary": (
            "A body check is legal only against an opponent in possession of the ball or "
            "within five yards of a loose ball, from the front or side, above the waist and "
            "below the shoulders. Checking a defenseless or unaware player, hitting from "
            "behind, above the shoulders (targeting the head/neck), or below the waist is an "
            "illegal body check and a personal foul, escalating with the severity of the hit."
        ),
    },
    "slash": {
        "call_type": "Slashing",
        "rule_applied": "Rule 5, Section 8 — Slashing (personal foul)",
        "summary": (
            "Slashing is swinging the crosse at an opponent's body with deliberate or "
            "reckless force, or a one-handed check. Controlled stick checks to the "
            "opponent's gloves or crosse in a legal attempt to dislodge the ball are not "
            "slashing; a forceful or uncontrolled swing to the body, head, or a "
            "non-checkable area is a personal foul."
        ),
    },
    "push": {
        "call_type": "Pushing",
        "rule_applied": "Rule 6, Section 9 — Pushing (technical foul)",
        "summary": (
            "Pushing is exerting pressure to an opponent's back, or pushing an opponent not "
            "in possession of the ball. A push is legal only from the front or side against "
            "a ball carrier or a player within five yards of a loose ball; pushing from "
            "behind is a technical foul."
        ),
    },
    "crease_violation": {
        "call_type": "Crease Violation",
        "rule_applied": "Rule 4, Section 18 / Rule 6 — Goalie crease (technical foul)",
        "summary": (
            "An attacking player may not step into the goal crease, and a goal is "
            "disallowed if an offensive player enters the crease before or as the ball "
            "crosses the line, or dives and lands in the crease. Contact with the "
            "goalkeeper while they have possession within the crease is also a violation."
        ),
    },
    "offside": {
        "call_type": "Offside",
        "rule_applied": "Rule 6, Section 5 — Offside (technical foul)",
        "summary": (
            "A team is offside when it has more than six players (excluding penalty-box "
            "players) on the attack half or more than seven on the defensive half of the "
            "field, i.e. it fails to keep the required number of players on its side of the "
            "midline. Offside is a technical foul that turns the ball over or nullifies a goal."
        ),
    },
    "loose_ball_push": {
        "call_type": "Loose-Ball Push",
        "rule_applied": "Rule 6, Section 9 — Pushing during a loose ball (technical foul)",
        "summary": (
            "During a loose ball, contact is legal only against a player within five yards "
            "of the ball, and only from the front or side. Pushing or bodying an opponent "
            "who is more than five yards from the loose ball, or pushing from behind while "
            "pursuing it, is a technical foul."
        ),
    },
}
