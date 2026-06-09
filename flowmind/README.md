# FlowMind v0.1.1-alpha

Local AI gateway with automatic provider failover.

## Features

- **Provider Priority** — configure the order to try: Gemini → OpenRouter → NVIDIA
- **Multi-Key Support** — add unlimited API keys per provider; FlowMind rotates them automatically
- **Failover Engine** — on a 429 (quota exceeded) or server error, FlowMind tries the next key, then the next provider — no interruption
- **OpenAI-Compatible Endpoint** — `POST /v1/chat/completions`
- **Anthropic-Compatible Endpoint** — `POST /v1/messages` (works with Claude Code and Anthropic SDKs)

## Quick Start

```bash
pip install .
flowmind setup      # configure keys and priority
flowmind start      # launch on :4000
```

## Setup Wizard

`flowmind setup` will ask for:
1. API keys for each provider (enter multiple keys per provider for rotation)
2. Provider priority order (e.g. 1 2 3 for Gemini → OpenRouter → NVIDIA)

Config is saved to `~/.flowmind.json`.

## Failover Logic

```
Gemini Key 1 → 429
  Gemini Key 2 → 429
    OpenRouter Key 1 → success ✓
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/v1/providers` | List providers and key counts |
| POST | `/v1/chat/completions` | OpenAI-compatible (tools, agents) |
| POST | `/v1/messages` | Anthropic-compatible (Claude Code, SDKs) |

## Config Schema

```json
{
  "provider_priority": ["gemini", "openrouter", "nvidia"],
  "gemini":     ["key1", "key2"],
  "openrouter": ["key1"],
  "nvidia":     []
}
```

## Commands

```
flowmind setup    Configure API keys and provider priority
flowmind start    Start the local gateway on :4000
flowmind doctor   Check configuration
flowmind version  Show version
```
