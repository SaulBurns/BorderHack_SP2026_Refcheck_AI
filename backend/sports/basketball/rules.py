"""Basketball rule-retrieval boosts (Sprint 9 — moved out of generic retrieval).

Sport-specific keyword nudges that push the generic keyword retriever toward the
right NBA rule. Moved verbatim (same rule_ids, trigger terms, and point values)
from `services/analysis/retrieval.py` so the basketball scoring lives with the
sport. Each rule matches at most its own id, so at most one boost applies.
"""

from __future__ import annotations

# (rule_id, trigger terms, boost points)
_BOOSTS: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("BLOCK_CHARGE", ("charge", "blocking", "guarding", "lateral", "torso", "established"), 6),
    ("RESTRICTED_AREA", ("restricted", "secondary", "paint", "lane", "basket"), 8),
    ("VERTICALITY", ("vertical", "cylinder", "straight", "landing", "forward"), 7),
    ("AIRBORNE_SHOOTER", ("airborne", "shooter", "upward", "landing", "shooting"), 7),
    ("INCIDENTAL_CONTACT", ("incidental", "rhythm", "speed", "balance", "quickness", "marginal"), 7),
    ("SHOOTING_CONTACT", ("shoot", "shooter", "airborne", "arm", "landing", "verticality"), 6),
    ("TRAVEL", ("travel", "pivot", "gather", "steps", "dribble"), 6),
    ("OUT_OF_BOUNDS", ("out", "boundary", "sideline", "baseline", "last"), 6),
    ("GOALTENDING", ("goaltend", "downward", "cylinder", "rim", "interference"), 6),
)


def boost_rule_score(rule_id: str, haystack: str) -> int:
    """Extra score for a candidate rule given the retrieval haystack (0 if none)."""
    for rid, terms, points in _BOOSTS:
        if rule_id == rid and any(term in haystack for term in terms):
            return points
    return 0
