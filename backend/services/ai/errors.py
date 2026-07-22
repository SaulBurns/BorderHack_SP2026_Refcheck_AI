"""Provider error taxonomy (Sprint 16D — reliability).

Providers raise these classified exceptions so the transport-retry layer
(`services/ai/reliability.py`) knows what is safe to retry:

- ``TransientProviderError`` — a temporary failure worth retrying (rate limit,
  5xx/overloaded, timeout, dropped connection).
- ``PermanentProviderError`` — a failure retrying cannot fix (bad request, auth,
  permission, not found). **Never retried.**

All three subclass ``RuntimeError``, so the pipeline's existing ``except`` (which
degrades to the mock fallback) still catches them unchanged. Validation failures
are a *separate* class handled one layer up in ``_send_validated`` — they never
reach this taxonomy.
"""

from __future__ import annotations


class ProviderError(RuntimeError):
    """Base class for a classified provider-communication failure."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        status: int | None = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status = status


class TransientProviderError(ProviderError):
    """A temporary failure that is safe to retry with backoff."""


class PermanentProviderError(ProviderError):
    """A failure retrying cannot fix — raised immediately, never retried."""


# HTTP statuses worth retrying: request timeout, conflict, rate limit, and any 5xx
# (500-599, which includes Anthropic's 529 "overloaded").
_RETRYABLE_STATUS = {408, 409, 429}


def is_retryable_status(status: int) -> bool:
    return status in _RETRYABLE_STATUS or 500 <= status < 600


def classify_http_status(status: int, message: str, **ctx) -> ProviderError:
    """Map an HTTP status to a transient/permanent provider error.

    Transient: 408/409/429 and all 5xx (incl. 529). Everything else — 400 (bad
    request), 401 (auth), 403 (permission), 404 (not found), other 4xx — is
    permanent and must not be retried.
    """
    cls = TransientProviderError if is_retryable_status(status) else PermanentProviderError
    return cls(message, status=status, **ctx)
