"""Lacrosse sport plugin (Sprint 12 — fourth sport).

Exposes ``LacrosseSport``, the full ``Sport`` implementation for men's field
lacrosse. Registered in ``sports/registry.py``; the pipeline resolves it with
``get_sport("lacrosse")`` and delegates all lacrosse-specific behavior to it.

Layout::

    sports/lacrosse/
        prompts.py       # perception / retrieval / adjudicator prompts
        rules.py         # rule-retrieval boosts (corpus lives in rules/lacrosse_rules.py)
        tracking.py      # tracked-evidence layer (possession, ball movement)
        extractor.py     # LacrosseDetailExtractor -> LacrosseDetails
        game_context.py  # metadata provider seam (None in Sprint 12)
        sport.py         # LacrosseSport wiring
"""

from sports.lacrosse.sport import LacrosseSport

__all__ = ["LacrosseSport"]
