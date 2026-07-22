"""Transport retry, backoff, and provider-comms health (Sprint 16D).

`call_with_retry` wraps a single provider call and retries **only**
`TransientProviderError` with exponential backoff + jitter. Permanent errors and
any other exception propagate immediately, so auth / bad-request / (higher-layer)
validation failures are never retried. On success or after exhausting retries it
records a `ProviderHealth` entry and, on exhaustion, re-raises the last transient
error with an enriched message naming the provider, model, attempt count, and total
latency — clear diagnostics that flow into the pipeline's `fallback_reason`.

`sleep`/`monotonic` are injectable so the backoff schedule is deterministically
unit-testable without real delays.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from services import config
from services.ai.errors import ProviderError, TransientProviderError


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential-backoff policy for transient provider failures."""

    max_retries: int = 2          # retries after the first attempt (total = max_retries + 1)
    base_delay: float = 0.5       # seconds; delay for the first retry
    max_delay: float = 8.0        # seconds; cap
    jitter: float = 0.1           # fraction of the delay added as random jitter

    @property
    def max_attempts(self) -> int:
        return self.max_retries + 1

    def delay_for(self, retry_index: int, rand: float) -> float:
        """Backoff delay before retry `retry_index` (0-based). `rand` ∈ [0,1)."""
        raw = self.base_delay * (2 ** retry_index)
        capped = min(self.max_delay, raw)
        return capped + capped * self.jitter * rand


def retry_policy_from_config() -> RetryPolicy:
    return RetryPolicy(
        max_retries=max(0, config.env_int(config.PROVIDER_MAX_RETRIES_ENV, config.DEFAULT_PROVIDER_MAX_RETRIES)),
        base_delay=config.env_float(config.PROVIDER_BACKOFF_BASE_SECONDS_ENV, config.DEFAULT_PROVIDER_BACKOFF_BASE_SECONDS),
        max_delay=config.env_float(config.PROVIDER_BACKOFF_MAX_SECONDS_ENV, config.DEFAULT_PROVIDER_BACKOFF_MAX_SECONDS),
    )


# ---------------------------------------------------------------------------
# Provider-comms health record (process-local; thread-safe).
# ---------------------------------------------------------------------------

@dataclass
class _Health:
    calls: int = 0
    retries: int = 0
    failures: int = 0
    last_outcome: str | None = None       # "success" | "transient_exhausted" | "permanent"
    last_provider: str | None = None
    last_model: str | None = None
    last_latency_ms: float | None = None
    last_attempts: int | None = None
    last_error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


_HEALTH = _Health()


def _record(*, outcome: str, provider: str, model: str, attempts: int, latency_ms: float, error: str | None) -> None:
    with _HEALTH._lock:
        _HEALTH.calls += 1
        _HEALTH.retries += max(0, attempts - 1)
        if outcome != "success":
            _HEALTH.failures += 1
        _HEALTH.last_outcome = outcome
        _HEALTH.last_provider = provider
        _HEALTH.last_model = model
        _HEALTH.last_attempts = attempts
        _HEALTH.last_latency_ms = round(latency_ms, 2)
        _HEALTH.last_error = error


def provider_health() -> dict:
    """Snapshot of provider-communication health (for readiness/diagnostics)."""
    with _HEALTH._lock:
        healthy = _HEALTH.last_outcome in (None, "success")
        return {
            "ok": healthy,
            "calls": _HEALTH.calls,
            "retries": _HEALTH.retries,
            "failures": _HEALTH.failures,
            "last_outcome": _HEALTH.last_outcome,
            "last_provider": _HEALTH.last_provider,
            "last_model": _HEALTH.last_model,
            "last_attempts": _HEALTH.last_attempts,
            "last_latency_ms": _HEALTH.last_latency_ms,
            "last_error": _HEALTH.last_error,
        }


def reset_provider_health() -> None:
    """Reset the health record (tests)."""
    global _HEALTH
    _HEALTH = _Health()


# ---------------------------------------------------------------------------
# The retry loop.
# ---------------------------------------------------------------------------

def call_with_retry(
    fn: Callable[[], str],
    *,
    provider: str,
    model: str,
    policy: RetryPolicy | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    rng: Callable[[], float] = random.random,
) -> str:
    """Run `fn()`, retrying only `TransientProviderError` with backoff.

    Returns `fn()`'s result on success. Re-raises `PermanentProviderError` and any
    non-transient exception immediately (no retry). On transient exhaustion re-raises
    the last `TransientProviderError` with an enriched, diagnostic message.
    """
    policy = policy or retry_policy_from_config()
    started = monotonic()
    last_exc: TransientProviderError | None = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = fn()
        except TransientProviderError as exc:
            last_exc = exc
            if attempt < policy.max_attempts:
                sleep(policy.delay_for(attempt - 1, rng()))
                continue
            # Exhausted — record and re-raise with diagnostics.
            latency_ms = (monotonic() - started) * 1000.0
            _record(
                outcome="transient_exhausted", provider=provider, model=model,
                attempts=attempt, latency_ms=latency_ms, error=str(exc),
            )
            raise TransientProviderError(
                f"{provider} provider call failed after {attempt} attempt(s) "
                f"(model={model}, {latency_ms:.0f}ms): {exc}",
                provider=provider, model=model, status=exc.status,
            ) from exc
        except ProviderError as exc:  # permanent (or any other classified) — do not retry
            latency_ms = (monotonic() - started) * 1000.0
            _record(
                outcome="permanent", provider=provider, model=model,
                attempts=attempt, latency_ms=latency_ms, error=str(exc),
            )
            raise
        else:
            latency_ms = (monotonic() - started) * 1000.0
            _record(
                outcome="success", provider=provider, model=model,
                attempts=attempt, latency_ms=latency_ms, error=None,
            )
            return result

    # Unreachable (the loop always returns or raises), but keeps type checkers happy.
    raise last_exc  # pragma: no cover
