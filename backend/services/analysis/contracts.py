"""Typed contracts for the pipeline payloads (Sprint 7).

The pipeline historically passed bare ``dict`` / ``list[dict]`` between agents,
which the audit flagged as the main typing gap. These ``TypedDict``s document
those structurally-fixed shapes and let a type checker catch key drift (e.g. the
rule-record dict was built with slightly different keys in three places).

They are annotation-only: because every pipeline module uses
``from __future__ import annotations``, referencing these types adds no runtime
import cost and does not validate or reshape anything — behavior is unchanged.
``PerceptionDict``/``TrackedEvidence`` stay loose (``dict[str, Any]``) because they
are produced by the model / detection layer and read defensively with ``.get``.
"""

from __future__ import annotations

from typing import Any, TypedDict

# Perception and tracked evidence are model/detector-produced and read with
# `.get(...)` defaults throughout, so they intentionally stay open dicts.
PerceptionDict = dict[str, Any]
TrackedEvidence = dict[str, Any]


class RuleRecord(TypedDict, total=False):
    """A retrieved rulebook record. `similarity_score` only on the fallback."""

    rule_id: str
    section_title: str
    text: str
    page_number: int
    call_type: str
    similarity_score: float


class AdjudicatorOutput(TypedDict, total=False):
    """Raw adjudicator verdict as parsed from a model reply (all keys optional)."""

    verdict: str
    confidence: float
    primary_rule_id: str | None
    supporting_rule_ids: list[str]
    reasoning: str
    flags: list[str]


class AgentResult(TypedDict, total=False):
    """The internal result of the four-agent pipeline, consumed by _build_response."""

    provider_used: str
    detector: str
    fallback_reason: str | None
    retrieval_query: str
    retrieved_rules: list[RuleRecord]
    perception: PerceptionDict
    detections: Any  # RawDetections | None (kept loose to avoid an import cycle)
    tracked_evidence: TrackedEvidence | None
    adjudicator_a: AdjudicatorOutput
    adjudicator_b: AdjudicatorOutput
