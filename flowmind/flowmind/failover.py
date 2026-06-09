"""FlowMind Failover Engine.

Tries each key for a provider in sequence, then falls over to the next
provider in the configured priority list.  Returns the first successful
response or raises the last exception encountered.

Usage (called from server.py):
    from flowmind.failover import call_with_failover
    response_json = await call_with_failover(payload, stream=False)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

import flowmind.config as cfg
from flowmind.providers import gemini, openrouter, nvidia

logger = logging.getLogger("flowmind.failover")

_PROVIDER_MODULES = {
    "gemini":     gemini,
    "openrouter": openrouter,
    "nvidia":     nvidia,
}

# HTTP status codes that trigger key/provider rotation
_RETRY_STATUSES = {429, 500, 502, 503, 504}


class AllProvidersExhausted(Exception):
    """Raised when every key and every provider has been tried."""


async def call_with_failover(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Try every key for every provider (in priority order).
    Returns the first successful JSON response dict.
    Raises AllProvidersExhausted if nothing works.
    """
    priority = cfg.get_provider_priority()
    last_error: Exception | None = None

    for provider_name in priority:
        mod = _PROVIDER_MODULES.get(provider_name)
        if mod is None:
            logger.warning("Unknown provider %r — skipping", provider_name)
            continue

        keys = cfg.get_keys(provider_name)
        if not keys:
            logger.debug("No keys for %s — skipping", provider_name)
            continue

        for idx, api_key in enumerate(keys):
            logger.debug("Trying %s key %d/%d", provider_name, idx + 1, len(keys))
            try:
                result = await _attempt(mod, api_key, payload)
                logger.info("Success via %s key %d", provider_name, idx + 1)
                # Annotate which provider/key actually served the request
                result.setdefault("_flowmind", {}).update(
                    {"provider": provider_name, "key_index": idx}
                )
                return result
            except _RetryableError as exc:
                logger.warning(
                    "%s key %d failed (%s) — trying next", provider_name, idx + 1, exc
                )
                last_error = exc
            except Exception as exc:
                # Non-retryable (e.g. 400 bad request) — surface immediately
                raise

    raise AllProvidersExhausted(
        f"All providers exhausted. Last error: {last_error}"
    ) from last_error


# ── Internal helpers ─────────────────────────────────────────────────────────

class _RetryableError(Exception):
    """Wraps errors that should trigger key/provider rotation."""


async def _attempt(mod, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Make one HTTP request.  Raises _RetryableError on quota/server errors."""
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    extra = getattr(mod, "EXTRA_HEADERS", {})
    headers.update(extra)

    url = f"{mod.BASE_URL}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        raise _RetryableError(f"network error: {exc}") from exc

    if resp.status_code in _RETRY_STATUSES:
        raise _RetryableError(f"HTTP {resp.status_code}: {resp.text[:200]}")

    if resp.status_code != 200:
        # Non-retryable — let it propagate
        from fastapi import HTTPException
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"{mod.PROVIDER_NAME} API error: {resp.text[:400]}",
        )

    return resp.json()
