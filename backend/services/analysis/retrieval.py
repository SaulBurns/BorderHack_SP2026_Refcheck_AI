"""Keyword rulebook retrieval + ranking (Sprint 7 extraction).

Heuristic (non-embedding) retrieval: score the static rule corpus against a
perception-derived haystack. Records + ranking are cached; the corpus is
loaded lazily from rules.sport_config. Behavior is unchanged."""

from __future__ import annotations

from functools import lru_cache

from services.analysis.contracts import PerceptionDict, RuleRecord


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


def _retrieve_rules(query: str, perception: PerceptionDict, sport: str, limit: int = 5) -> list[RuleRecord]:
    defender_status = perception.get("defender_status") or {}
    court_geometry = perception.get("court_geometry") or {}
    haystack = (
        f"{query} {perception.get('event_type', '')} {perception.get('summary', '')} "
        f"{perception.get('offensive_control_status', '')} "
        f"{court_geometry.get('key_zone', '')} "
        f"{defender_status.get('primary_or_secondary', '')} "
        f"{defender_status.get('legal_guarding_position', '')} "
        f"{defender_status.get('moving_direction', '')}"
    ).lower()
    # Ranking is a pure function of (haystack, sport, limit); memoize it so
    # repeated identical retrievals (demo/benchmark loops) skip re-scoring.
    return list(_rank_rules(haystack, sport, limit))


@lru_cache(maxsize=256)
def _rank_rules(haystack: str, sport: str, limit: int) -> tuple[RuleRecord, ...]:
    scored: list[tuple[int, RuleRecord]] = []
    for rule in _rule_records(sport):
        rule_text = (
            f"{rule['rule_id']} {rule['section_title']} {rule['text']} {rule['call_type']}"
        ).lower()
        score = sum(1 for term in haystack.split() if term in rule_text)

        if sport == "basketball":
            if rule["rule_id"] == "BLOCK_CHARGE" and any(
                t in haystack for t in ["charge", "blocking", "guarding", "lateral", "torso", "established"]
            ):
                score += 6
            if rule["rule_id"] == "RESTRICTED_AREA" and any(
                t in haystack for t in ["restricted", "secondary", "paint", "lane", "basket"]
            ):
                score += 8
            if rule["rule_id"] == "VERTICALITY" and any(
                t in haystack for t in ["vertical", "cylinder", "straight", "landing", "forward"]
            ):
                score += 7
            if rule["rule_id"] == "AIRBORNE_SHOOTER" and any(
                t in haystack for t in ["airborne", "shooter", "upward", "landing", "shooting"]
            ):
                score += 7
            if rule["rule_id"] == "INCIDENTAL_CONTACT" and any(
                t in haystack for t in ["incidental", "rhythm", "speed", "balance", "quickness", "marginal"]
            ):
                score += 7
            if rule["rule_id"] == "SHOOTING_CONTACT" and any(
                t in haystack for t in ["shoot", "shooter", "airborne", "arm", "landing", "verticality"]
            ):
                score += 6
            if rule["rule_id"] == "TRAVEL" and any(
                t in haystack for t in ["travel", "pivot", "gather", "steps", "dribble"]
            ):
                score += 6
            if rule["rule_id"] == "OUT_OF_BOUNDS" and any(
                t in haystack for t in ["out", "boundary", "sideline", "baseline", "last"]
            ):
                score += 6
            if rule["rule_id"] == "GOALTENDING" and any(
                t in haystack for t in ["goaltend", "downward", "cylinder", "rim", "interference"]
            ):
                score += 6

        scored.append((score, rule))

    return tuple(
        rule for _, rule in sorted(scored, key=lambda item: item[0], reverse=True)
    )[:limit]


def _rules_text(rules: list[RuleRecord]) -> str:
    return "\n\n".join(
        f"[{rule['rule_id']} | page {rule['page_number']}]\n"
        f"{rule['section_title']}\n"
        f"{rule['text']}"
        for rule in rules
    )
