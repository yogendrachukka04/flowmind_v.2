# FlowMind v0.1.0-alpha

Local AI gateway with provider routing. One endpoint, three providers, zero lock-in.

## Install

```bash
pip install -e .
```

## Quick start

```bash
# 1. Configure your API keys
flowmind setup

# 2. Start the gateway
flowmind start

# 3. Health check
curl localhost:4000/health

# 4. Chat
curl -s localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
```

## Commands

| Command           | Description                          |
|-------------------|--------------------------------------|
| `flowmind setup`  | Configure API keys (~/.flowmind.json)|
| `flowmind start`  | Start gateway on :4000               |
| `flowmind doctor` | Verify config and key status         |
| `flowmind version`| Show version                         |

## Endpoints

| Method | Path                    | Description                         |
|--------|-------------------------|-------------------------------------|
| GET    | `/health`               | Liveness probe                      |
| GET    | `/v1/providers`         | List providers and active selection |
| POST   | `/v1/chat/completions`  | OpenAI-compatible chat              |

## Providers

| Provider    | Default Model              | Priority |
|-------------|----------------------------|----------|
| Gemini      | gemini-1.5-flash           | 1        |
| OpenRouter  | openai/gpt-4o-mini         | 2        |
| NVIDIA NIM  | meta/llama-3.1-8b-instruct | 3        |

## Config file

`~/.flowmind.json` is created by `flowmind setup`:

```json
{
  "gemini": "AIza...",
  "openrouter": "sk-or-...",
  "nvidia": "nvapi-...",
  "active_provider": "gemini"
}
```

The file is `chmod 600` — readable only by you.

## Stub mode

No API key? FlowMind still starts and returns structured stub responses so you can verify routing before spending any credits.

## Roadmap

- **Week 2** — Provider failover
- **Week 3** — API key rotation
- **Week 4** — Session state
- **Week 5** — Snapshot memory
