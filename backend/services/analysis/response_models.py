"""Pydantic models for the raw model replies (Sprint 16B — structured outputs).

Every model-produced payload in the pipeline is validated against one of these
models before it is used:

- ``PerceptionResponse`` — the perception agent's structured observation.
- ``AdjudicatorResponse`` — one adjudicator's verdict.

The pipeline (`services/ai_analyzer._send_validated`) calls ``model_validate_json``
on the raw provider text — Pydantic parses the JSON **and** validates it in one
step, so there is no hand-rolled `json.loads` and no regex extraction. A
``ValidationError`` (malformed JSON *or* schema mismatch) triggers a bounded retry;
the validated model is then ``model_dump()``-ed back to a plain dict so every
downstream reader is unchanged.

``model_json_schema()`` on these models is also handed to the provider as the
``response_schema`` for native structured output (Gemini JSON mode + schema,
Anthropic ``output_config.format``). Both models are intentionally **flat** (no
nested ``BaseModel`` fields → no ``$defs``/``$ref``), so the generated schema is a
single clean object every provider accepts.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdjudicatorResponse(BaseModel):
    """One adjudicator's verdict.

    ``verdict`` and ``confidence`` are required — a reply missing either is a
    validation failure and is retried. ``reasoning`` is optional (some replies omit
    it; `_frontend_adjudicator` supplies a default). Extra keys are ignored (a model
    may add fields we don't consume). Downstream code (`_reconcile`,
    `_frontend_adjudicator`) reads this via ``model_dump()``, so the on-wire
    ``/api/analyze`` shape is unchanged.
    """

    model_config = ConfigDict(extra="ignore")

    verdict: str
    confidence: float
    reasoning: str = ""
    primary_rule_id: str | None = None
    supporting_rule_ids: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class PerceptionResponse(BaseModel):
    """The perception agent's structured observation.

    Deliberately permissive: only ``event_type`` and ``summary`` are required (a
    reply missing them is retried), every other field the frontend reads stays
    optional, and ``extra="allow"`` lets the full, sport-specific perception body
    pass through untouched. Nested blocks are typed as open ``dict``/``list`` so the
    generated JSON Schema stays flat and provider-friendly.
    """

    model_config = ConfigDict(extra="allow")

    event_type: str
    summary: str
    sport: str | None = None
    players_involved: list[Any] = Field(default_factory=list)
    contact_detected: bool | None = None
    contact_location: str | None = None
    ball_visible: bool | None = None
    ball_state: str | None = None
    offensive_control_status: str | None = None
    defender_status: dict[str, Any] | None = None
    court_geometry: dict[str, Any] | None = None
    frame_observations: list[Any] = Field(default_factory=list)
    moment_of_interest_seconds: float | None = None
    impact_zone: dict[str, Any] | None = None
    visual_quality: str | None = None
    perception_confidence: float | None = None
    notes: str | None = None
