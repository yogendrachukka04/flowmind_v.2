"""OpenRouter provider constants and model helpers."""

PROVIDER_NAME = "openrouter"
BASE_URL      = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"

MODELS = [
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-haiku",
    "google/gemini-flash-1.5",
    "meta-llama/llama-3.1-70b-instruct",
    "mistralai/mistral-7b-instruct",
]

EXTRA_HEADERS = {
    "HTTP-Referer": "https://flowmind.local",
    "X-Title": "FlowMind",
}


def resolve(requested: str) -> str:
    if requested in MODELS:
        return requested
    lower = requested.lower()
    if "claude" in lower:
        return "anthropic/claude-3.5-sonnet"
    if "gpt" in lower:
        return "openai/gpt-4o-mini"
    if "llama" in lower:
        return "meta-llama/llama-3.1-70b-instruct"
    if "mistral" in lower:
        return "mistralai/mistral-7b-instruct"
    return DEFAULT_MODEL
