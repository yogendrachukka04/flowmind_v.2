"""Gemini provider constants and model helpers."""

PROVIDER_NAME = "gemini"
BASE_URL      = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MODEL = "gemini-1.5-flash"

MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-pro",
]


def resolve(requested: str) -> str:
    if requested in MODELS:
        return requested
    if "pro" in requested.lower():
        return "gemini-1.5-pro"
    return DEFAULT_MODEL
