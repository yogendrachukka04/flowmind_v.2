"""NVIDIA NIM provider constants and model helpers."""

PROVIDER_NAME = "nvidia"
BASE_URL      = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"

MODELS = [
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-405b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
    "nvidia/nemotron-4-340b-instruct",
]


def resolve(requested: str) -> str:
    if requested in MODELS:
        return requested
    lower = requested.lower()
    if "70b" in lower:
        return "meta/llama-3.1-70b-instruct"
    if "405b" in lower:
        return "meta/llama-3.1-405b-instruct"
    if "mistral" in lower:
        return "mistralai/mistral-7b-instruct-v0.3"
    return DEFAULT_MODEL
