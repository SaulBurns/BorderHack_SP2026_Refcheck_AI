"""Soccer rule-retrieval boosts (Sprint 10).

Sport-specific keyword nudges that push the generic keyword retriever toward the
right Law of the Game. Same mechanism as ``sports/basketball/rules.py``: each
tuple is (rule_id, trigger terms, boost points), each rule matches at most its
own id, so at most one boost applies. The rule corpus itself lives in
``rules/soccer_rules.py``; this file only tunes ranking.

Terms are matched against the retrieval haystack (query + event_type + summary +
soccer perception signals), so they use plain-language soccer vocabulary the
perception/retrieval agents actually emit.
"""

from __future__ import annotations

# (rule_id, trigger terms, boost points)
_BOOSTS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("PENALTY", ("penalty", "penalty_area", "in_penalty_area", "box", "spot", "18-yard"), 8),
    ("OFFSIDE", ("offside", "offside_relevant", "onside", "defender", "line", "interfering"), 8),
    ("HANDBALL", ("handball", "hand", "arm", "handball_candidate", "silhouette", "deliberate"), 8),
    ("RED_CARD", ("red", "sending-off", "dogso", "violent", "serious", "excessive"), 7),
    ("YELLOW_CARD", ("yellow", "caution", "reckless", "unsporting", "simulation", "dive", "tactical"), 7),
    ("FOUL", ("foul", "trip", "push", "hold", "tackle", "kick", "charge", "careless"), 6),
    ("GOAL", ("goal", "goal_line", "crossbar", "posts", "over", "line"), 6),
)


def boost_rule_score(rule_id: str, haystack: str) -> int:
    """Extra score for a candidate rule given the retrieval haystack (0 if none)."""
    for rid, terms, points in _BOOSTS:
        if rule_id == rid and any(term in haystack for term in terms):
            return points
    return 0
