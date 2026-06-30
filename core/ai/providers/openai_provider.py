"""core/ai/providers/openai_provider.py — OpenAI provider implementation."""
import importlib
from typing import Any

from core.ai.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider using the openai SDK.
    """

    def __init__(self, api_key: str, model: str, client: Any | None = None):
        super().__init__(api_key, model)
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        openai_module = importlib.import_module("openai")
        self._client = openai_module.OpenAI(api_key=self.api_key)
        return self._client

    def generate(
        self,
        system_prompt: str,
        contents: str,
        message_history: list[dict[str, str]] | None = None,
    ) -> str:
        client = self._get_client()

        # Build messages structure
        messages = [{"role": "system", "content": system_prompt}]
        if message_history:
            messages.extend(message_history)
        else:
            messages.append({"role": "user", "content": contents})

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )

        # Extract text from response
        choices = getattr(response, "choices", None)
        if choices:
            first_choice = choices[0]
            message = getattr(first_choice, "message", None)
            if message:
                text = getattr(message, "content", "")
                if isinstance(text, str) and text.strip():
                    return text.strip()

        raise RuntimeError("OpenAI API response did not include any text content.")
