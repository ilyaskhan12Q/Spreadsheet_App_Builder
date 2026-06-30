"""core/ai/providers/factory.py — AI Provider factory."""
from typing import Any, Literal

from core.ai.providers.base import BaseProvider
from core.ai.providers.claude_provider import ClaudeProvider
from core.ai.providers.gemini_provider import GeminiProvider
from core.ai.providers.openai_provider import OpenAIProvider

AIProviderName = Literal["claude", "gemini", "openai"]

PROVIDER_MAP = {
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
}


def get_provider(
    provider_name: AIProviderName,
    api_key: str,
    model: str,
    client: Any | None = None,
) -> BaseProvider:
    """
    Get an instance of a provider class.

    Parameters
    ----------
    provider_name : {"claude", "gemini", "openai"}
        Name of the AI provider.
    api_key : str
        API key for the provider.
    model : str
        Model identifier.
    client : Optional[Any]
        Optional pre-instantiated client for testing.

    Returns
    -------
    BaseProvider
    """
    if provider_name not in PROVIDER_MAP:
        raise ValueError(
            f"Unsupported provider: {provider_name!r}. "
            f"Supported providers: {list(PROVIDER_MAP.keys())}"
        )

    provider_cls = PROVIDER_MAP[provider_name]
    return provider_cls(api_key=api_key, model=model, client=client)  # type: ignore[abstract]
