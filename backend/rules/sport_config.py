"""Sport configuration seams — now fully registry-driven.

The sport list, display names, and rule corpora are no longer a hardcoded table
here: they are owned by the Sport plugins (`sports/<sport>/`) and resolved through
the `SportRegistry`. This module keeps `normalize_sport()` /
`get_rules_for_sport()` / `supported_sports()` as the stable seams the pipeline
calls, each delegating to the registry so adding a sport never edits this file.
"""

from __future__ import annotations


def supported_sports() -> frozenset[str]:
    """The set of registered sport names (registry-driven)."""
    from sports import registry
    return frozenset(registry.available())


def sport_display_names() -> dict[str, str]:
    """Map of registered sport name -> human-readable display name."""
    from sports import get_sport
    return {name: get_sport(name).display_name for name in supported_sports()}


# NOTE: normalize_sport() and get_rules_for_sport() have different fallback behavior
# by design. normalize_sport() always returns a valid sport key (falling back to
# "basketball" for unknowns) and is called ONCE at the pipeline entry point.
# get_rules_for_sport() returns {} for unregistered sports and is called with
# already-normalized values — it never sees unknown sport strings in production.


def normalize_sport(sport: str | None) -> str:
    """Lowercase and strip the value; return 'basketball' for unregistered sports."""
    normalized = sport.lower().strip() if sport else ""
    return normalized if normalized in supported_sports() else "basketball"


def get_rules_for_sport(sport: str) -> dict:
    """Return the rules corpus for a sport, resolved from its plugin.

    Returns an empty dict for unregistered sport strings (GenericSport). Always
    call normalize_sport() before passing sport to pipeline functions that use
    this function.
    """
    from sports import get_sport
    return get_sport(sport).rule_records()
