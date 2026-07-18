"""Keyword rulebook retrieval + ranking (Sprint 7 extraction; Sprint 14 scoring).

Heuristic (non-embedding) retrieval: score the static rule corpus against a
perception-derived haystack. Records + ranking are cached; the corpus is loaded
lazily from rules.sport_config.

Sprint 14 — better retrieval. The scorer moved from raw substring counting to
tokenized, stopword-filtered, **field-weighted** whole-word overlap: a query term
that lands in a rule's id / section title / call type (its "label" fields) counts
for more than one buried in the body text, and common stopwords no longer inflate
scores. The haystack is now built sport-agnostically from the perception summary +
event type + a flattened view of ``sport_details`` (plus the legacy basketball
fields, which are simply empty for other sports), so retrieval reads the same for
every sport. Sport-specific boosts (owned by the plugin) still apply on top.
"""

from __future__ import annotations

import re
from functools import lru_cache

from services.analysis.contracts import PerceptionDict, RuleRecord

# Weight for a query term matched in a rule's label fields (rule_id / section
# title / call type) vs. its body text. Label matches are stronger topical signals.
_LABEL_WEIGHT = 3
_BODY_WEIGHT = 1

# Common English stopwords + generic officiating filler that carry no topical
# signal; dropped from the haystack so they never inflate a rule's score.
_STOPWORDS: frozenset[str] = frozenset(
    """
    a an and are as at be been being by for from had has have in into is it its
    of on or that the their then this to was were what when which who with within
    unclear none unknown play player players call called original whether during
    """.split()
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    """Lowercase alphanumeric tokens with stopwords and 1-char noise removed."""
    return [
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) > 1 and token not in _STOPWORDS
    ]


@lru_cache(maxsize=16)
def _rule_records(sport: str) -> tuple[RuleRecord, ...]:
    """Static rulebook records for a sport.

    Cached (Sprint 6 perf): the records never change at runtime, yet this was
    rebuilt — and `rules.sport_config` re-imported — on every retrieval call
    (once per analysis). Returned as an immutable tuple; callers only read.
    """
    from rules.sport_config import get_rules_for_sport
    return tuple(
        {
            "rule_id": key.upper(),
            "section_title": rule["rule_applied"],
            "text": rule["summary"],
            "page_number": rule.get("page_number", 1),
            "call_type": rule["call_type"],
        }
        for key, rule in get_rules_for_sport(sport).items()
    )


def _flatten_values(value: object) -> list[str]:
    """Collect the string/scalar leaves of a nested sport_details block."""
    out: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            out.extend(_flatten_values(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            out.extend(_flatten_values(item))
    elif isinstance(value, str):
        out.append(value)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        out.append(str(value))
    return out


def _build_haystack(query: str, perception: PerceptionDict, sport: str) -> str:
    """Sport-agnostic retrieval haystack.

    Combines the query with the perception summary/event type and a flattened view
    of the sport's ``sport_details`` block, so the same builder works for every
    sport. Legacy basketball top-level fields are still included (they are empty
    for other sports), preserving basketball behavior exactly.
    """
    sport_details = perception.get("sport_details") or {}
    detail_values = _flatten_values(sport_details.get(sport)) if isinstance(sport_details, dict) else []

    # Legacy basketball-shaped fields (present only for basketball); harmless
    # empty strings for other sports.
    defender_status = perception.get("defender_status") or {}
    court_geometry = perception.get("court_geometry") or {}

    parts = [
        query,
        str(perception.get("event_type", "")),
        str(perception.get("summary", "")),
        str(perception.get("contact_location", "")),
        str(perception.get("ball_state", "")),
        str(perception.get("offensive_control_status", "")),
        str(court_geometry.get("key_zone", "")),
        str(defender_status.get("primary_or_secondary", "")),
        str(defender_status.get("legal_guarding_position", "")),
        str(defender_status.get("moving_direction", "")),
        *detail_values,
    ]
    return " ".join(part for part in parts if part)


def _retrieve_rules(
    query: str, perception: PerceptionDict, sport: str, limit: int = 5
) -> list[RuleRecord]:
    haystack = _build_haystack(query, perception, sport).lower()
    # Ranking is a pure function of (haystack, sport, limit); memoize it so
    # repeated identical retrievals (demo/benchmark loops) skip re-scoring.
    return list(_rank_rules(haystack, sport, limit))


def _sport_boost(sport: str, rule_id: str, haystack: str) -> int:
    """Sport-specific retrieval boost, owned by the Sport plugin (Sprint 9).

    Lazy import breaks the sports<->services import cycle. Non-basketball sports
    return 0, so ranking is unchanged for them.
    """
    from sports import get_sport
    return get_sport(sport).boost_rule_score(rule_id, haystack)


def _keyword_score(haystack_tokens: frozenset[str], rule: RuleRecord) -> int:
    """Field-weighted whole-word overlap between the haystack and one rule.

    A query token matched in the rule's label fields (id / section title / call
    type) scores `_LABEL_WEIGHT`; one matched only in the body text scores
    `_BODY_WEIGHT`. Whole-word (token) matching avoids the substring false matches
    of the previous scorer (e.g. "in" matching "point").
    """
    label_tokens = frozenset(
        _tokens(f"{rule['rule_id']} {rule['section_title']} {rule['call_type']}")
    )
    body_tokens = frozenset(_tokens(rule["text"]))
    score = 0
    for token in haystack_tokens:
        if token in label_tokens:
            score += _LABEL_WEIGHT
        elif token in body_tokens:
            score += _BODY_WEIGHT
    return score


@lru_cache(maxsize=256)
def _rank_rules(haystack: str, sport: str, limit: int) -> tuple[RuleRecord, ...]:
    haystack_tokens = frozenset(_tokens(haystack))
    scored: list[tuple[int, int, RuleRecord]] = []
    for index, rule in enumerate(_rule_records(sport)):
        score = _keyword_score(haystack_tokens, rule)
        score += _sport_boost(sport, rule["rule_id"], haystack)
        # index is a stable tiebreaker so equal-scoring rules keep corpus order.
        scored.append((score, -index, rule))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return tuple(rule for _, _, rule in scored)[:limit]


def _rules_text(rules: list[RuleRecord]) -> str:
    return "\n\n".join(
        f"[{rule['rule_id']} | page {rule['page_number']}]\n"
        f"{rule['section_title']}\n"
        f"{rule['text']}"
        for rule in rules
    )
