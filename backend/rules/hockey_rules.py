"""Hockey rulebook corpus (Sprint 11 — second new sport).

Keyword-retrievable rule records for ice hockey, mirroring the shape of
``rules/basketball_rules.py`` and ``rules/soccer_rules.py``: each entry has a
``call_type``, ``rule_applied``, and ``summary``. Keys are lowercase and become
the uppercase ``rule_id`` used by retrieval, adjudication citations, and the
demo/eval datasets.

Coverage is scoped to the Sprint 11 supported events: icing, offside, tripping,
cross-checking, boarding, slashing, and hooking. Summaries paraphrase the NHL
rulebook in plain, reviewer-facing language — they are a retrieval corpus, not a
legal citation.
"""

HOCKEY_RULES = {
    "icing": {
        "call_type": "Icing",
        "rule_applied": "Rule 81 — Icing (puck shot from behind center across the goal line)",
        "summary": (
            "Icing occurs when a player, from their own half of the ice (behind the "
            "center red line), shoots the puck across the opponents' goal line without it "
            "being touched. Play is stopped and a faceoff returns to the offending team's "
            "defensive zone. Icing is waved off if the team is short-handed, if the puck "
            "crosses through the goal crease, or (under no-touch/hybrid rules) if a "
            "defending player could have played it first."
        ),
    },
    "offside": {
        "call_type": "Offside",
        "rule_applied": "Rule 83 — Off-side (preceding the puck into the attacking zone)",
        "summary": (
            "A player is offside if both skates completely cross the attacking blue line "
            "before the puck. Position is determined by the skates, not the stick; a "
            "player straddling the blue line with one skate on the line is onside. The "
            "linesman stops play for offside, with a faceoff outside the zone."
        ),
    },
    "tripping": {
        "call_type": "Tripping",
        "rule_applied": "Rule 57 — Tripping (stick, foot, or leg causing an opponent to fall)",
        "summary": (
            "A minor penalty is assessed to a player who uses the stick, knee, foot, arm, "
            "hand, or elbow to cause an opponent to trip or fall. A legal poke-check that "
            "contacts the puck first is not tripping; if a player is dispossessed cleanly "
            "and then falls over the defender's stick, no penalty results."
        ),
    },
    "cross_checking": {
        "call_type": "Cross-checking",
        "rule_applied": "Rule 59 — Cross-checking (check delivered with both hands and no stick on ice)",
        "summary": (
            "Cross-checking is a check delivered with the shaft of the stick held in both "
            "hands and no part of the stick on the ice. A minor or major penalty is "
            "assessed depending on severity, and a major plus game misconduct if an injury "
            "results, especially to the head or neck area."
        ),
    },
    "boarding": {
        "call_type": "Boarding",
        "rule_applied": "Rule 41 — Boarding (checking an opponent violently into the boards)",
        "summary": (
            "Boarding is checking, pushing, or tripping an opponent so violently that they "
            "are thrown into the boards. The onus is on the checking player to avoid a "
            "defenseless opponent; the severity of the check and the position of the "
            "opponent (turned, defenseless) determine a minor, major, or match penalty."
        ),
    },
    "slashing": {
        "call_type": "Slashing",
        "rule_applied": "Rule 61 — Slashing (swinging the stick at an opponent)",
        "summary": (
            "Slashing is swinging the stick at an opponent, whether or not contact is "
            "made. A forceful chop on the body or hands, or any slash that causes injury, "
            "escalates to a major and game misconduct. Non-forceful stick contact incidental "
            "to a play on the puck is generally not penalized."
        ),
    },
    "hooking": {
        "call_type": "Hooking",
        "rule_applied": "Rule 55 — Hooking (using the stick to impede an opponent's progress)",
        "summary": (
            "Hooking is applying the blade or shaft of the stick to an opponent's body or "
            "stick to restrain or impede their progress. A tug that visibly slows the "
            "opponent or causes them to lose the puck is a minor penalty; a legal stick "
            "position on the puck without restraining the opponent is not hooking."
        ),
    },
}
