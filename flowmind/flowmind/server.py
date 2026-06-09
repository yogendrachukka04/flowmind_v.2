"""FlowMind Local Gateway — FastAPI server on :4000.

Endpoints
---------
GET  /health                  liveness probe
GET  /v1/providers            list configured providers
POST /v1/chat/completions     OpenAI-compatible chat  (with failover)
POST /v1/messages             Anthropic-compatible chat (with failover)
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from flowmind import __version__
import flowmind.config as cfg
from flowmind.providers import gemini, openrouter, nvidia
from flowmind.failover import AllProvidersExhausted
from flowmind.router import route

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FlowMind",
    version=__version__,
    description="Local AI gateway with provider routing and automatic failover",
)

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, Any] = {
    "gemini":     gemini,
    "openrouter": openrouter,
    "nvidia":     nvidia,
}

# ---------------------------------------------------------------------------
# Models — OpenAI-compatible
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
# Models — Anthropic-compatible (/v1/messages)
# ---------------------------------------------------------------------------

class AnthropicMessage(BaseModel):
    role: str
    content: str


class AnthropicRequest(BaseModel):
    model: str = "claude-3-5-sonnet-20241022"
    messages: list[AnthropicMessage]
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    system: Optional[str] = None
    stream: bool = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Liveness probe."""
    priority = cfg.get_provider_priority()
    providers_status = []
    for p in priority:
        keys = cfg.get_keys(p)
        providers_status.append({"provider": p, "keys": len(keys)})
    return {
        "status":            "healthy",
        "version":           __version__,
        "provider_priority": priority,
        "providers":         providers_status,
    }


@app.get("/v1/providers")
def list_providers():
    """Return all providers, key counts, and priority order."""
    config = cfg.load()
    priority = cfg.get_provider_priority()
    result = []
    for name, mod in _PROVIDERS.items():
        keys = cfg.get_keys(name)
        result.append({
            "name":          name,
            "priority_rank": priority.index(name) + 1 if name in priority else None,
            "key_count":     len(keys),
            "default_model": mod.DEFAULT_MODEL,
            "base_url":      mod.BASE_URL,
        })
    result.sort(key=lambda x: (x["priority_rank"] or 99))
    return {"providers": result, "priority": priority}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    """
    OpenAI-compatible chat completions with automatic failover.

    Routes through providers in priority order, rotating keys on 429s.
    Falls back to a stub response only if no keys are configured at all.
    """
    priority = cfg.get_provider_priority()
    has_any_key = any(cfg.get_keys(p) for p in priority)

    if not has_any_key:
        return _stub_response(priority[0] if priority else "gemini", "default", req)

    messages = [m.model_dump() for m in req.messages]
    try:
        result = await route(req.model, messages, req.temperature, req.max_tokens)
        return JSONResponse(content=result)
    except AllProvidersExhausted as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/v1/messages")
async def anthropic_messages(req: AnthropicRequest):
    """
    Anthropic-compatible messages endpoint.

    Accepts requests in the Anthropic SDK / Claude Code format and proxies
    them through FlowMind's failover engine.  The response is translated back
    into Anthropic's response shape so callers need no changes.
    """
    priority = cfg.get_provider_priority()
    has_any_key = any(cfg.get_keys(p) for p in priority)

    # Build OpenAI-style messages (inject system prompt if present)
    messages: list[dict] = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.extend({"role": m.role, "content": m.content} for m in req.messages)

    if not has_any_key:
        return _anthropic_stub_response(req)

    try:
        openai_resp = await route(req.model, messages, req.temperature, req.max_tokens)
    except AllProvidersExhausted as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Translate OpenAI response → Anthropic response shape
    return JSONResponse(content=_to_anthropic_response(openai_resp, req.model))


# ---------------------------------------------------------------------------
# Response translators
# ---------------------------------------------------------------------------

def _to_anthropic_response(openai_resp: dict, model: str) -> dict:
    """Convert an OpenAI-format completion to an Anthropic /v1/messages shape."""
    choices = openai_resp.get("choices", [])
    text = choices[0]["message"]["content"] if choices else ""
    usage = openai_resp.get("usage", {})
    return {
        "id":      f"msg_{uuid.uuid4().hex[:24]}",
        "type":    "message",
        "role":    "assistant",
        "content": [{"type": "text", "text": text}],
        "model":   openai_resp.get("model", model),
        "stop_reason":    choices[0].get("finish_reason", "end_turn") if choices else "end_turn",
        "stop_sequence":  None,
        "usage": {
            "input_tokens":  usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
        "_flowmind": openai_resp.get("_flowmind", {}),
    }


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
                    f"[FlowMind stub — no keys configured]\n"
                    f"You said: {last_user_msg}"
                ),
            },
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "_flowmind": {"provider": provider, "stub": True},
    }


def _anthropic_stub_response(req: AnthropicRequest) -> dict:
    last_user_msg = next(
        (m.content for m in reversed(req.messages) if m.role == "user"),
        "(no message)",
    )
    return {
        "id":      f"msg_{uuid.uuid4().hex[:24]}",
        "type":    "message",
        "role":    "assistant",
        "content": [{"type": "text", "text": f"[FlowMind stub — no keys configured]\nYou said: {last_user_msg}"}],
        "model":   req.model,
        "stop_reason":   "end_turn",
        "stop_sequence": None,
        "usage":   {"input_tokens": 0, "output_tokens": 0},
        "_flowmind": {"stub": True},
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

    priority = cfg.get_provider_priority()
    print(f"FlowMind v{__version__} starting on http://{host}:{port}")
    print(f"Provider priority : {' → '.join(priority)}")
    print(f"Health check      : http://localhost:{port}/health")
    print(f"OpenAI endpoint   : http://localhost:{port}/v1/chat/completions")
    print(f"Anthropic endpoint: http://localhost:{port}/v1/messages")
    print("Press Ctrl+C to stop.\n")

    uvicorn.run(app, host=host, port=port, log_level="info")
