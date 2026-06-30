"""core/ai/providers/claude_provider.py — Claude provider implementation."""
import importlib
from typing import Any

from core.ai.providers.base import BaseProvider


class ClaudeProvider(BaseProvider):
    """
    Claude provider using the anthropic SDK.
    """

    def __init__(self, api_key: str, model: str, client: Any | None = None):
        super().__init__(api_key, model)
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        anthropic_module = importlib.import_module("anthropic")
        self._client = anthropic_module.Anthropic(api_key=self.api_key)
        return self._client

    def generate(
        self,
        system_prompt: str,
        contents: str,
        message_history: list[dict[str, str]] | None = None,
    ) -> str:
        client = self._get_client()

        # Build messages structure
        messages = []
        if message_history:
            messages.extend(message_history)
        else:
            messages.append({"role": "user", "content": contents})

        response = client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=system_prompt,
            messages=messages,
        )

        # Extract text from response
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        content = getattr(response, "content", None)
        if content:
            first_block = content[0]
            block_text = getattr(first_block, "text", "")
            if isinstance(block_text, str):
                return block_text.strip()

        raise RuntimeError("Claude API response did not include any text content.")
