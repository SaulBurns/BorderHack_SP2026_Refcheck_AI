"""Canonical verdict vocabulary + normalization (Sprint 7).

The triple `("fair_call", "bad_call", "inconclusive")` and its
synonym→canonical maps were re-typed in four places (the pipeline's
`_frontend_verdict`, the demo suite's `_VERDICT_ALIASES`, and the evaluation
model). This module is the single source of truth.

- `normalize_verdict` is LENIENT: it accepts sponsor/perception synonyms and any
  casing/spacing and defaults to "inconclusive" for anything unrecognized. Used
  by the pipeline and demo tooling where inputs are free-form.
- Strict validation (raise on unknown) stays in `evaluation` because it uses that
  module's own error type; it imports `VERDICTS` from here so the tuple is shared.
"""

from __future__ import annotations

VERDICTS: tuple[str, str, str] = ("fair_call", "bad_call", "inconclusive")

# Synonym -> canonical verdict. Superset of every map that previously existed;
# no synonym maps to two different canonical verdicts, so the merge is lossless.
_ALIASES: dict[str, str] = {
    "fair": "fair_call",
    "fair_call": "fair_call",
    "good_call": "fair_call",
    "correct": "fair_call",
    "correct_call": "fair_call",
    "upheld": "fair_call",
    "bad": "bad_call",
    "bad_call": "bad_call",
    "missed_call": "bad_call",
    "incorrect": "bad_call",
    "incorrect_call": "bad_call",
    "wrong_call": "bad_call",
    "overturned": "bad_call",
    "inconclusive": "inconclusive",
    "unclear": "inconclusive",
}


def normalize_verdict(value: str | None) -> str:
    """Map a free-form verdict string to a canonical verdict.

    Case/space-insensitive; unrecognized input becomes "inconclusive".
    """
    normalized = (value or "").lower().strip().replace(" ", "_")
    return _ALIASES.get(normalized, "inconclusive")
