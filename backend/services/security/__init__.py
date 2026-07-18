"""Production security primitives (Sprint 15): API-key auth + rate limiting.

Both are **off by default** so demos, tests, and existing deployments are
unaffected, and both are pure/testable in isolation:

- `auth` — optional `X-API-Key` / `Bearer` verification, enforced only when
  `API_KEYS` (or `REFCHECK_API_KEY`) is configured.
- `rate_limit` — a fixed-window per-client limiter, enabled by setting
  `RATE_LIMIT_PER_MINUTE`.
"""

from services.security.auth import api_key_auth, auth_enabled, configured_api_keys, verify_api_key
from services.security.rate_limit import RateLimiter, rate_limit_per_minute

__all__ = [
    "api_key_auth",
    "auth_enabled",
    "configured_api_keys",
    "verify_api_key",
    "RateLimiter",
    "rate_limit_per_minute",
]
