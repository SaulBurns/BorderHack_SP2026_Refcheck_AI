"""Per-call token-usage accounting for benchmarking (Sprint 17D).

The benchmark needs to compare providers on **token usage** and **cost**, not just
accuracy and latency. `send_messages` returns only text, so this module is the
process-local recorder every real provider call reports into (via
`ai_analyzer._call_provider`), keyed by the concrete model that ran.

Design boundaries:
- **Off by default** — `record()` is a no-op until `enable()` is called, so the
  production pipeline pays zero overhead and accumulates no state. Only the
  benchmark turns it on, resets per run, and reads a snapshot.
- **Estimated tokens** — counts come from prompt/reply text length (a chars-per-token
  heuristic) plus a flat per-image estimate. Deterministic, offline, and
  provider-neutral, so mixed-provider comparisons use one consistent yardstick
  rather than each vendor's differently-defined "token". Clearly labelled as an
  estimate everywhere it surfaces.
- **Thread-safe** — the two adjudicators run concurrently, so records take a lock
  (same pattern as `reliability.provider_health`).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

# Rough bytes/char-per-token ratio. English text averages ~4 chars/token across
# both Claude and Gemini tokenizers — good enough for a relative comparison.
CHARS_PER_TOKEN = 4
# Flat per-image token estimate (a vision frame costs far more than its bytes of
# text). Both Claude and Gemini bill images in the high-hundreds/low-thousands of
# tokens; 1000 is a neutral midpoint for the comparison.
IMAGE_TOKEN_ESTIMATE = 1000


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string (ceil of chars / CHARS_PER_TOKEN)."""
    if not text:
        return 0
    return -(-len(text) // CHARS_PER_TOKEN)  # ceil division


def estimate_content_tokens(user_content) -> int:
    """Estimate tokens for provider-neutral `user_content` (str or content parts)."""
    if isinstance(user_content, str):
        return estimate_tokens(user_content)
    total = 0
    for part in user_content:
        if part.get("type") == "image":
            total += IMAGE_TOKEN_ESTIMATE
        else:
            total += estimate_tokens(part.get("text", ""))
    return total


@dataclass
class _ModelUsage:
    provider: str
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class _Recorder:
    enabled: bool = False
    by_model: dict[str, _ModelUsage] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


_RECORDER = _Recorder()


def enable() -> None:
    _RECORDER.enabled = True


def disable() -> None:
    _RECORDER.enabled = False


def is_enabled() -> bool:
    return _RECORDER.enabled


def reset() -> None:
    """Clear recorded usage (called by the benchmark before each combo run)."""
    with _RECORDER._lock:
        _RECORDER.by_model = {}


def record(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    """Record one provider call's token usage. No-op unless tracking is enabled."""
    if not _RECORDER.enabled:
        return
    with _RECORDER._lock:
        entry = _RECORDER.by_model.get(model)
        if entry is None:
            entry = _ModelUsage(provider=provider)
            _RECORDER.by_model[model] = entry
        entry.calls += 1
        entry.prompt_tokens += max(0, prompt_tokens)
        entry.completion_tokens += max(0, completion_tokens)


def record_call(*, provider: str, model: str, system_prompt: str, user_content, reply: str) -> None:
    """Estimate tokens from a call's prompt + reply and record them (no-op if off)."""
    if not _RECORDER.enabled:
        return
    prompt_tokens = estimate_tokens(system_prompt) + estimate_content_tokens(user_content)
    completion_tokens = estimate_tokens(reply)
    record(provider, model, prompt_tokens, completion_tokens)


def snapshot() -> dict:
    """Aggregate usage snapshot: totals plus a per-model breakdown."""
    with _RECORDER._lock:
        by_model = {model: usage.to_dict() for model, usage in _RECORDER.by_model.items()}
    calls = sum(m["calls"] for m in by_model.values())
    prompt_tokens = sum(m["prompt_tokens"] for m in by_model.values())
    completion_tokens = sum(m["completion_tokens"] for m in by_model.values())
    return {
        "calls": calls,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "by_model": by_model,
    }
