"""core/ai/providers/gemini_provider.py — Gemini provider implementation."""
import importlib
from typing import Any

from core.ai.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    """
    Gemini provider using the google-genai SDK.
    """

    def __init__(self, api_key: str, model: str, client: Any | None = None):
        super().__init__(api_key, model)
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        genai_module = importlib.import_module("google.genai")
        self._client = genai_module.Client(api_key=self.api_key)
        return self._client

    def generate(
        self,
        system_prompt: str,
        contents: str,
        message_history: list[dict[str, str]] | None = None,
    ) -> str:
        client = self._get_client()

        # Build contents/history structure for Gemini generate_content call.
        # If there is multi-turn correction history, format it.
        # Otherwise, just send user contents.
        if message_history:
            # Format history into a prompt string for gemini or use content parts.
            # To stay robust across SDK changes, we format history into a single prompt block:
            history_blocks = []
            for msg in message_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prefix = "User" if role == "user" else "Assistant"
                history_blocks.append(f"[{prefix}]:\n{content}")
            prompt_input = "\n\n".join(history_blocks)
        else:
            prompt_input = contents

        try:
            types_module = importlib.import_module("google.genai.types")
            config = types_module.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            )
        except ModuleNotFoundError:
            config = {
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
            }

        response = client.models.generate_content(
            model=self.model,
            contents=prompt_input,
            config=config,
        )

        # Extract text from response
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        candidates = getattr(response, "candidates", None)
        if candidates:
            first_candidate = candidates[0]
            candidate_content = getattr(first_candidate, "content", None)
            if candidate_content:
                parts = getattr(candidate_content, "parts", None) or []
                if parts:
                    part_text = getattr(parts[0], "text", "")
                    if isinstance(part_text, str):
                        return part_text.strip()

        raise RuntimeError("Gemini API response did not include any text content.")
