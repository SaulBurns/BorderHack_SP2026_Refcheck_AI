"""Sport rule corpus loading + formatting (Sprint 16A).

The pipeline injects each sport's **complete** rule corpus directly into the
adjudicator prompts — the corpora are small (6-9 rules per sport), so there is no
retrieval/ranking stage. This module owns two pure helpers:

- ``_rule_records(sport)`` — the sport's full rulebook as immutable ``RuleRecord``s
  (cached; loaded lazily from ``rules.sport_config``).
- ``_rules_text(rules)`` — renders those records into the block the adjudicator
  prompt embeds.

An unregistered sport resolves to an empty corpus (``GenericSport``), so the
adjudicator still runs Claude-only with no rules to cite.

History: this module was ``retrieval.py`` and scored a keyword haystack to pick
the top 5 rules. Sprint 16A removed the Retrieval stage entirely; the ranking
machinery (and the ``Sport.boost_rule_score`` seam it used) is gone.
"""

from __future__ import annotations

from functools import lru_cache

from services.analysis.contracts import RuleRecord


@lru_cache(maxsize=16)
def _rule_records(sport: str) -> tuple[RuleRecord, ...]:
    """The sport's complete rulebook records.

    Cached: the records never change at runtime. Returned as an immutable tuple;
    callers only read (and copy into a list when a mutable corpus is needed).
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


def _rules_text(rules: list[RuleRecord]) -> str:
    return "\n\n".join(
        f"[{rule['rule_id']} | page {rule['page_number']}]\n"
        f"{rule['section_title']}\n"
        f"{rule['text']}"
        for rule in rules
    )
