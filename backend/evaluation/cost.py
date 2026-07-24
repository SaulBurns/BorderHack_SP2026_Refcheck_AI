"""Model pricing and cost estimation for the benchmark (Sprint 17D).

Turns a token-usage snapshot (`services.ai.usage.snapshot`) into a dollar cost by
applying per-model list prices. Pure and dependency-free so it unit-tests offline.

Prices are **USD per 1,000,000 tokens, (input, output)** — published list prices,
kept here as the single editable source of truth. They change over time; update
this table (or override via `PRICING`) rather than hard-coding costs elsewhere.
Costs are labelled **estimated** everywhere they surface: token counts are
estimates (see `services/ai/usage.py`) and prices are list, not negotiated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# model id -> (input $/1M, output $/1M). Anthropic prices per the Claude pricing
# reference; Gemini per Google's public list pricing (both as of 2026-07).
PRICING: dict[str, tuple[float, float]] = {
    # Anthropic (Claude)
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    # Google (Gemini)
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-1.5-flash": (0.075, 0.30),
    # Offline / test providers cost nothing.
    "mock": (0.0, 0.0),
}


def price_for(model: str) -> tuple[float, float] | None:
    """(input, output) $/1M for `model`, or None when the model isn't priced."""
    return PRICING.get(model)


def cost_for_model(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """USD cost for one model's token usage (0.0 when the model isn't priced)."""
    price = price_for(model)
    if price is None:
        return 0.0
    input_price, output_price = price
    return (prompt_tokens / 1_000_000) * input_price + (completion_tokens / 1_000_000) * output_price


@dataclass(frozen=True)
class CostSummary:
    """Estimated dollar cost for a benchmark run, with a per-model breakdown."""

    total_usd: float
    by_model: dict = field(default_factory=dict)  # model -> {usd, priced}
    estimated: bool = True

    @classmethod
    def from_usage_snapshot(cls, snapshot: dict) -> "CostSummary":
        by_model: dict = {}
        total = 0.0
        for model, usage in snapshot.get("by_model", {}).items():
            usd = cost_for_model(model, usage["prompt_tokens"], usage["completion_tokens"])
            by_model[model] = {"usd": round(usd, 6), "priced": price_for(model) is not None}
            total += usd
        return cls(total_usd=round(total, 6), by_model=by_model, estimated=True)

    def to_dict(self) -> dict:
        return {"total_usd": self.total_usd, "by_model": self.by_model, "estimated": self.estimated}


@dataclass(frozen=True)
class TokenUsage:
    """Token totals for a benchmark run, with a per-model breakdown."""

    calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    by_model: dict = field(default_factory=dict)

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> "TokenUsage":
        return cls(
            calls=snapshot.get("calls", 0),
            prompt_tokens=snapshot.get("prompt_tokens", 0),
            completion_tokens=snapshot.get("completion_tokens", 0),
            total_tokens=snapshot.get("total_tokens", 0),
            by_model=dict(snapshot.get("by_model", {})),
        )

    def to_dict(self) -> dict:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "by_model": self.by_model,
        }
