"""Lacrosse rule-retrieval boosts (Sprint 12).

Sport-specific keyword nudges that push the generic keyword retriever toward the
right rule. Same mechanism as the other sports' ``rules.py``: each tuple is
(rule_id, trigger terms, boost points), each rule matches at most its own id, so
at most one boost applies. The rule corpus itself lives in
``rules/lacrosse_rules.py``; this file only tunes ranking.

Note on PUSH vs. LOOSE_BALL_PUSH: both concern pushing, so their trigger terms are
deliberately disjoint — PUSH keys only on possession-context vocabulary (back,
pressure, in possession) and LOOSE_BALL_PUSH only on loose-ball vocabulary — so a
loose-ball scenario boosts the loose-ball rule and a possession push boosts the
pushing rule. (The bare word "push" is intentionally NOT a trigger for either,
since it appears in both rules' text and is already scored by the base keyword
retriever.)
"""

from __future__ import annotations

# (rule_id, trigger terms, boost points)
_BOOSTS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("ILLEGAL_BODY_CHECK", ("body check", "body_check", "defenseless", "blindside", "targeting", "late hit"), 8),
    ("CREASE_VIOLATION", ("crease", "crease_violation", "dive", "goal crease", "goalkeeper", "goalie"), 8),
    ("OFFSIDE", ("offside", "midline", "restraining", "players per", "too many players"), 8),
    ("SLASH", ("slash", "slashing", "one-handed", "crosse", "swing", "chop", "stick check"), 7),
    ("LOOSE_BALL_PUSH", ("loose ball", "loose_ball", "loose", "five yards", "5 yards", "within five"), 7),
    ("PUSH", ("shove", "back", "pressure", "in possession"), 6),
)


def boost_rule_score(rule_id: str, haystack: str) -> int:
    """Extra score for a candidate rule given the retrieval haystack (0 if none)."""
    for rid, terms, points in _BOOSTS:
        if rule_id == rid and any(term in haystack for term in terms):
            return points
    return 0
