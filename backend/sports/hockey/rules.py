"""Hockey rule-retrieval boosts (Sprint 11).

Sport-specific keyword nudges that push the generic keyword retriever toward the
right NHL rule. Same mechanism as ``sports/basketball/rules.py`` and
``sports/soccer/rules.py``: each tuple is (rule_id, trigger terms, boost points),
each rule matches at most its own id, so at most one boost applies. The rule
corpus itself lives in ``rules/hockey_rules.py``; this file only tunes ranking.

Terms are matched against the retrieval haystack (query + event_type + summary +
hockey perception signals), so they use plain-language hockey vocabulary the
perception/retrieval agents actually emit.
"""

from __future__ import annotations

# (rule_id, trigger terms, boost points)
_BOOSTS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("ICING", ("icing", "red line", "goal line", "dumped", "untouched", "waved"), 8),
    ("OFFSIDE", ("offside", "blue line", "skates", "attacking zone", "preceding", "zone entry"), 8),
    ("CROSS_CHECKING", ("cross", "cross_checking", "cross-check", "both hands", "shaft", "checking"), 8),
    ("BOARDING", ("boarding", "boards", "boards_involved", "defenseless", "turned", "along_boards"), 8),
    ("SLASHING", ("slash", "slashing", "swing", "chop", "stick blade", "hands"), 7),
    ("HOOKING", ("hook", "hooking", "impede", "restrain", "tug", "blade"), 7),
    ("TRIPPING", ("trip", "tripping", "fall", "poke-check", "leg", "foot", "stick"), 6),
)


def boost_rule_score(rule_id: str, haystack: str) -> int:
    """Extra score for a candidate rule given the retrieval haystack (0 if none)."""
    for rid, terms, points in _BOOSTS:
        if rule_id == rid and any(term in haystack for term in terms):
            return points
    return 0
