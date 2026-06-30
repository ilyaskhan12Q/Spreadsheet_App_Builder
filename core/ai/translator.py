"""core/ai/translator.py — AI Translation layer for AppSpec."""
import os
from typing import Any, Literal

from core.ai.providers import get_provider
from core.app_spec import AppSpec
from core.scanner.context_builder import SpreadsheetContext

AIProvider = Literal["claude", "gemini", "openai"]

DEFAULT_MODELS: dict[AIProvider, str] = {
    "claude": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o",
}

PROVIDER_KEY_ENV_VARS: dict[AIProvider, tuple[str, ...]] = {
    "claude": ("SAB_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
    "gemini": ("SAB_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "openai": ("SAB_OPENAI_API_KEY", "OPENAI_API_KEY"),
}


class TranslationError(Exception):
    """Raised when AITranslator fails to generate a valid AppSpec after retries."""

    pass


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if the model wraps JSON in a fenced block."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def resolve_provider_api_key(
    provider: AIProvider, api_key: str | None = None
) -> tuple[str | None, str | None]:
    """Resolve API key from parameter or environment variables."""
    if api_key:
        return api_key, "explicit API key"

    if provider not in PROVIDER_KEY_ENV_VARS:
        return None, None

    for env_var in PROVIDER_KEY_ENV_VARS[provider]:
        value = os.getenv(env_var)
        if value:
            return value, env_var

    return None, None


def describe_provider_setup(provider: AIProvider, api_key: str | None = None) -> str:
    """Return a short human-readable summary of the selected provider and key source."""
    resolved_key, source = resolve_provider_api_key(provider, api_key)
    if resolved_key and source:
        return f"{provider} configured via {source}"

    return f"{provider} configured without an API key"


class AITranslator:
    """
    Translates a user prompt and optional spreadsheet context into a semantic AppSpec JSON.
    """

    def __init__(
        self,
        api_key: str | None = None,
        provider: AIProvider = "claude",
        model: str | None = None,
        client: Any = None,
    ):
        if provider not in DEFAULT_MODELS:
            raise TranslationError(f"Unsupported AI provider: {provider!r}")

        self.provider: AIProvider = provider
        self.api_key = api_key or self._resolve_api_key(provider)
        self.model = model or DEFAULT_MODELS[provider]
        self.client = client

    def _resolve_api_key(self, provider: AIProvider) -> str | None:
        resolved_key, _ = resolve_provider_api_key(provider)
        return resolved_key

    def _get_system_prompt(self) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "system_prompt.txt")
        with open(prompt_path) as file_handle:
            return file_handle.read()

    def _build_prompt(self, prompt: str, context: SpreadsheetContext) -> str:
        return f"User Prompt: {prompt}\n\n{context.to_prompt_string()}"

    def translate(self, prompt: str, context: SpreadsheetContext) -> str:
        """
        Translates a user prompt + spreadsheet context into a raw AppSpec JSON string.
        Implements auto-correction retry on validation failure.
        """
        if not self.api_key and self.client is None:
            if self.provider == "claude":
                raise TranslationError(
                    "Claude provider requires SAB_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY."
                )
            elif self.provider == "gemini":
                raise TranslationError(
                    "Gemini provider requires SAB_GEMINI_API_KEY, GEMINI_API_KEY, or "
                    "GOOGLE_API_KEY."
                )
            else:
                raise TranslationError(
                    "OpenAI provider requires SAB_OPENAI_API_KEY or OPENAI_API_KEY."
                )

        system_prompt = self._get_system_prompt()
        base_prompt = self._build_prompt(prompt, context)
        max_retries = 2
        attempt = 0
        raw_json = ""
        correction_note = ""

        # Initialize the low-level provider wrapper via factory
        provider_client = get_provider(
            provider_name=self.provider,
            api_key=self.api_key or "fake-key",
            model=self.model,
            client=self.client,
        )

        message_history: list[dict[str, str]] = []

        while attempt <= max_retries:
            try:
                if self.provider == "claude" or self.provider == "openai":
                    if not message_history:
                        message_history.append({"role": "user", "content": base_prompt})
                    else:
                        assistant_content = raw_json or "Error: Empty response"
                        message_history.extend(
                            [
                                {"role": "assistant", "content": assistant_content},
                                {"role": "user", "content": correction_note},
                            ]
                        )
                    raw_json = provider_client.generate(
                        system_prompt=system_prompt,
                        contents=base_prompt,
                        message_history=message_history,
                    )
                else:
                    # Gemini or similar (no multi-turn structured messages supported)
                    contents = base_prompt
                    if correction_note:
                        prev_output = raw_json or "Error: Empty response"
                        contents = (
                            f"{base_prompt}\n\nPrevious output:\n{prev_output}\n\n"
                            f"Validation error:\n{correction_note}"
                        )
                    raw_json = provider_client.generate(
                        system_prompt=system_prompt,
                        contents=contents,
                    )

                raw_json = _strip_code_fences(raw_json)

                # Validate against AppSpec schema
                AppSpec.model_validate_json(raw_json)
                return raw_json

            except Exception as exc:
                attempt += 1
                if attempt > max_retries:
                    raise TranslationError(
                        f"Failed to translate and validate AppSpec after "
                        f"{max_retries} retries. Error: {exc}"
                    ) from exc

                correction_note = (
                    f"The output failed AppSpec validation with the following error:\n{exc}\n\n"
                    "Please correct the JSON AppSpec to comply with the schema and rules. "
                    "Do not include any explanation or markdown formatting, output raw JSON only."
                )

        raise TranslationError("Translation failed for unknown reasons during retry loop.")
