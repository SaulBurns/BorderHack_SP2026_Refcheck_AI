"""Hockey sport plugin (Sprint 11 — second new sport).

Exposes ``HockeySport``, the full ``Sport`` implementation for ice hockey.
Registered in ``sports/registry.py``; the pipeline resolves it with
``get_sport("hockey")`` and delegates all hockey-specific behavior to it.

Layout::

    sports/hockey/
        prompts.py       # perception / retrieval / adjudicator prompts
        rules.py         # rule-retrieval boosts (corpus lives in rules/hockey_rules.py)
        tracking.py      # tracked-evidence layer (puck possession, rush direction)
        extractor.py     # HockeyDetailExtractor -> HockeyDetails
        game_context.py  # metadata provider seam (None in Sprint 11)
        sport.py         # HockeySport wiring
"""

from sports.hockey.sport import HockeySport

__all__ = ["HockeySport"]
