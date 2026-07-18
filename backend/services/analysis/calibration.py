"""Confidence calibration for the reconciled verdict (Sprint 14).

The four-agent pipeline tends to be over-confident when the footage is only
partially usable: two adjudicators can agree on a verdict from a marginal angle
and still report 0.8+. This module shrinks the agreed confidence toward the
maximally-uncertain prior (0.5) as visual quality degrades — a monotonic,
information-preserving transform that lowers Expected Calibration Error without
changing any verdict.

Design constraints:
- Pure and side-effect free, so it is unit-testable in isolation.
- Identity for `visual_quality == "clear"`, so a well-conditioned clip's
  confidence (and every existing reconciliation test) is unchanged.
- Bounded to [0, 1]; never flips a verdict (it only scales the magnitude).
"""

from __future__ import annotations

# Prior for a maximally-uncertain binary-ish decision. Confidence is pulled toward
# this value as visibility drops.
_PRIOR = 0.5

# Fraction of the distance from the prior that survives at each visual-quality
# tier. 1.0 = no shrink (clear); < 1.0 = pull toward the prior (less certain).
_QUALITY_RETENTION: dict[str, float] = {
    "clear": 1.0,
    "partial": 0.85,
    "obstructed": 0.7,
    "poor": 0.6,
}
_DEFAULT_RETENTION = 0.85


def quality_retention(visual_quality: str | None) -> float:
    """Retention factor for a visual-quality label (unknown -> partial-tier)."""
    return _QUALITY_RETENTION.get((visual_quality or "").lower().strip(), _DEFAULT_RETENTION)


def calibrate_confidence(raw: float, visual_quality: str | None) -> float:
    """Shrink a raw confidence toward the 0.5 prior by the visual-quality factor.

    `clear` footage is returned unchanged; lower-quality footage is pulled toward
    0.5 (both over- and under-confident values move toward the prior). Result is
    clamped to [0, 1]. Not rounded — the caller applies its own rounding.
    """
    factor = quality_retention(visual_quality)
    calibrated = _PRIOR + factor * (raw - _PRIOR)
    return max(0.0, min(1.0, calibrated))
