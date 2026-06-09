"""FlowMind Local Gateway — FastAPI server on :4000.

Endpoints
---------
GET  /health                  liveness probe
GET  /v1/providers            list configured providers
POST /v1/chat/completions     OpenAI-compatible chat (proxies to active provider)
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from flowmind import __version__
import flowmind.config as cfg
from flowmind.providers import gemini, openrouter, nvidia

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FlowMind",
    version=__version__,
    description="Local AI gateway with provider routing",
)

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, Any] = {
    "gemini":     gemini,
    "openrouter": openrouter,
    "nvidia":     nvidia,
}


def _active_provider() -> str:
    config = cfg.load()
    return config.get("active_provider", "gemini")


def _provider_module(name: str):
    mod = _PROVIDERS.get(name)
    if mod is None:
        raise HTTPException(status_code=503, detail=f"Unknown provider: {name}")
    return mod


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "default"
    messages: list[Message]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    stream: bool = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Liveness probe."""
    provider = _active_provider()
    key = cfg.get_key(provider)
    return {
        "status":   "healthy",
        "version":  __version__,
        "provider": provider,
        "key_set":  bool(key),
    }


@app.get("/v1/providers")
def list_providers():
    """Return all providers and which is active."""
    config = cfg.load()
    active = config.get("active_provider", "gemini")
    result = []
    for name, mod in _PROVIDERS.items():
        key = config.get(name, "")
        result.append({
            "name":          name,
            "active":        name == active,
            "key_set":       bool(key),
            "default_model": mod.DEFAULT_MODEL,
            "base_url":      mod.BASE_URL,
        })
    return {"providers": result, "active": active}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    """
    OpenAI-compatible chat completions endpoint.

    Routes the request to the active provider using its base URL + API key.
    Falls back to a stub response if no key is configured (so curl tests always
    return something useful).
    """
    provider_name = _active_provider()
    mod           = _provider_module(provider_name)
    api_key       = cfg.get_key(provider_name)
    resolved_model = mod.resolve(req.model if req.model != "default" else mod.DEFAULT_MODEL)

    # ── Stub mode (no key) ──────────────────────────────────────────────────
    if not api_key:
        return _stub_response(provider_name, resolved_model, req)

    # ── Live proxy ──────────────────────────────────────────────────────────
    payload: dict[str, Any] = {
        "model":       resolved_model,
        "messages":    [m.model_dump() for m in req.messages],
        "temperature": req.temperature,
        "max_tokens":  req.max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    # OpenRouter wants extra courtesy headers
    extra = getattr(mod, "EXTRA_HEADERS", {})
    headers.update(extra)

    url = f"{mod.BASE_URL}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"{provider_name} API error: {resp.text[:400]}",
            )
        return JSONResponse(content=resp.json())

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"{provider_name} request timed out")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Network error: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stub_response(provider: str, model: str, req: ChatRequest) -> dict:
    """Return a well-formed stub when no API key is set."""
    last_user_msg = next(
        (m.content for m in reversed(req.messages) if m.role == "user"),
        "(no message)",
    )
    return {
        "id":      f"flowmind-stub-{uuid.uuid4().hex[:8]}",
        "object":  "chat.completion",
        "created": int(time.time()),
        "model":   model,
        "choices": [{
            "index":         0,
            "message": {
                "role":    "assistant",
                "content": (
                    f"[FlowMind stub — {provider} key not set]\n"
                    f"You said: {last_user_msg}"
                ),
            },
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "_flowmind": {"provider": provider, "stub": True},
    }


# ---------------------------------------------------------------------------
# start_server()  — called by `flowmind start`
# ---------------------------------------------------------------------------

def start_server(host: str = "0.0.0.0", port: int = 4000) -> None:
    import uvicorn

    config = cfg.load()
    if not config:
        print("⚠  No config found. Run `flowmind setup` first.")
        print("   Starting anyway in stub mode — API calls will return placeholder responses.\n")

    print(f"FlowMind v{__version__} starting on http://{host}:{port}")
    print(f"Active provider : {_active_provider()}")
    print(f"Health check    : http://localhost:{port}/health")
    print(f"Chat endpoint   : http://localhost:{port}/v1/chat/completions")
    print("Press Ctrl+C to stop.\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
