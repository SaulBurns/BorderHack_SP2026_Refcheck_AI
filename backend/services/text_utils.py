"""Small shared string helpers (Sprint 7).

Previously `_clean` was copy-pasted byte-for-byte in three modules
(`ai_analyzer`, `mock_analyzer`, `supabase_store`) and the rule-id transform was
inlined in four places. Centralized here so there is one implementation each.
"""

from __future__ import annotations


def clean(value: str | None, fallback: str = "") -> str:
    """Trim `value`; return `fallback` when it is None or blank after trimming."""
    if value is None:
        return fallback
    return value.strip() or fallback


def rule_id_from_call_type(call_type: str) -> str:
    """Canonical rule-id slug for a human call-type label.

    e.g. "Block / Charge" -> "BLOCK_CHARGE", "Out of Bounds" -> "OUT_OF_BOUNDS".
    """
    return call_type.upper().replace(" / ", "_").replace(" ", "_")
