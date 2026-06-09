"""FlowMind Router.

Resolves the correct model name for the target provider and assembles the
outbound payload, then delegates to the failover engine.

Usage:
    from flowmind.router import route
    response_json = await route(chat_request)
"""

from __future__ import annotations

from typing import Any

import flowmind.config as cfg
from flowmind.failover import call_with_failover
from flowmind.providers import gemini, openrouter, nvidia

_PROVIDER_MODULES = {
    "gemini":     gemini,
    "openrouter": openrouter,
    "nvidia":     nvidia,
}


async def route(model: str, messages: list[dict], temperature: float, max_tokens: int) -> dict[str, Any]:
    """
    Build the outbound payload and call the failover engine.

    The model name is resolved using the *first* provider in the priority
    list that has at least one key configured (best-effort; the failover
    engine may end up using a different provider if that one is down).
    """
    priority = cfg.get_provider_priority()

    # Pick the first configured provider for model resolution
    resolving_provider = "gemini"  # safe default
    for p in priority:
        if cfg.get_keys(p):
            resolving_provider = p
            break

    mod = _PROVIDER_MODULES.get(resolving_provider, gemini)
    resolved_model = mod.resolve(model if model != "default" else mod.DEFAULT_MODEL)

    payload: dict[str, Any] = {
        "model":       resolved_model,
        "messages":    messages,
        "temperature": temperature,
        "max_tokens":  max_tokens,
    }

    return await call_with_failover(payload)
