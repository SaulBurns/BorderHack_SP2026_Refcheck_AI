"""Optional API-key authentication (Sprint 15).

Enforced only when the operator configures keys — so the default build (demos,
tests, the current deployment) is completely unaffected. Configure one or more
keys via `API_KEYS` (comma-separated) or the single `REFCHECK_API_KEY`. Clients
then send `X-API-Key: <key>` or `Authorization: Bearer <key>` on the protected
(write) endpoints. Keys are compared in constant time.

`api_key_auth` is a FastAPI dependency; when no keys are configured it is a no-op,
so wiring it onto a route never changes behavior until keys are set.
"""

from __future__ import annotations

import hmac
import os

# Lazy imports of FastAPI types are avoided (they are light); the dependency reads
# headers off the Request so it needs no route-signature changes.
from fastapi import HTTPException, Request

API_KEYS_ENV = "API_KEYS"
SINGLE_API_KEY_ENV = "REFCHECK_API_KEY"


def configured_api_keys() -> frozenset[str]:
    """The set of accepted API keys from the environment (empty => auth disabled)."""
    keys: set[str] = set()
    raw_multi = os.getenv(API_KEYS_ENV, "")
    keys.update(part.strip() for part in raw_multi.split(",") if part.strip())
    single = os.getenv(SINGLE_API_KEY_ENV, "").strip()
    if single:
        keys.add(single)
    return frozenset(keys)


def auth_enabled() -> bool:
    """True when at least one API key is configured."""
    return bool(configured_api_keys())


def _extract_key(request: Request) -> str | None:
    header = request.headers.get("x-api-key")
    if header:
        return header.strip()
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def verify_api_key(provided: str | None) -> bool:
    """Constant-time membership check against the configured keys."""
    keys = configured_api_keys()
    if not keys:
        return True  # auth disabled
    if not provided:
        return False
    # Compare against every key in constant time (no early-exit timing signal).
    return any(hmac.compare_digest(provided, key) for key in keys)


async def api_key_auth(request: Request) -> None:
    """FastAPI dependency: allow when auth is disabled, else require a valid key.

    Records an auth-failure metric and raises 401 on rejection. Importing the
    metrics registry lazily keeps this module free of import cycles.
    """
    if not auth_enabled():
        return
    if verify_api_key(_extract_key(request)):
        return
    from services.observability.metrics import metrics

    metrics.inc("refcheck_auth_failures_total", {"path": request.url.path})
    raise HTTPException(
        status_code=401,
        detail="Missing or invalid API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )
