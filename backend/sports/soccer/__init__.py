"""Soccer sport plugin (Sprint 10 — first new sport).

Exposes ``SoccerSport``, the full ``Sport`` implementation for association
football. Registered in ``sports/registry.py``; the pipeline resolves it with
``get_sport("soccer")`` and delegates all soccer-specific behavior to it.

Layout::

    sports/soccer/
        prompts.py       # perception / adjudicator prompts
        tracking.py      # tracked-evidence layer (possession, ball movement)
        extractor.py     # SoccerDetailExtractor -> SoccerDetails
        game_context.py  # metadata provider seam (None in Sprint 10)
        sport.py         # SoccerSport wiring
"""

from sports.soccer.sport import SoccerSport

__all__ = ["SoccerSport"]
