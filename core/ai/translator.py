import importlib
import os
from typing import Any, Literal, Optional

from core.scanner.context_builder import SpreadsheetContext
from core.validator.schema import BlueprintValidator


AIProvider = Literal["claude", "gemini"]

DEFAULT_MODELS: dict[AIProvider, str] = {
    "claude": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.5-flash",
}

PROVIDER_KEY_ENV_VARS: dict[AIProvider, tuple[str, ...]] = {
    "claude": ("SAB_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
    "gemini": ("SAB_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
}


class TranslationError(Exception):
    """Raised when AITranslator fails to generate a valid blueprint after retries."""

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


def _extract_text_response(response: Any) -> str:
    """Normalize provider-specific response objects into plain text."""
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    content = getattr(response, "content", None)
    if content:
        first_block = content[0]
        block_text = getattr(first_block, "text", "")
        if isinstance(block_text, str):
            return block_text.strip()

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

    raise TranslationError("AI provider response did not include any text content.")


def resolve_provider_api_key(provider: AIProvider, api_key: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    if api_key:
        return api_key, "explicit API key"

    for env_var in PROVIDER_KEY_ENV_VARS[provider]:
        value = os.getenv(env_var)
        if value:
            return value, env_var

    return None, None


def describe_provider_setup(provider: AIProvider, api_key: Optional[str] = None) -> str:
    """
    Return a short human-readable summary of the selected provider and key source.
    """
    resolved_key, source = resolve_provider_api_key(provider, api_key)
    if resolved_key and source:
        return f"{provider} configured via {source}"

    return f"{provider} configured without an API key"


class AITranslator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: AIProvider = "claude",
        model: Optional[str] = None,
        client: Any = None,
    ):
        if provider not in DEFAULT_MODELS:
            raise TranslationError(f"Unsupported AI provider: {provider!r}")

        self.provider: AIProvider = provider
        self.api_key = api_key or self._resolve_api_key(provider)
        self.model = model or DEFAULT_MODELS[provider]
        self.client = client

    def _resolve_api_key(self, provider: AIProvider) -> Optional[str]:
        for env_var in PROVIDER_KEY_ENV_VARS[provider]:
            value = os.getenv(env_var)
            if value:
                return value
        return None

    def _get_system_prompt(self) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "system_prompt.txt")
        with open(prompt_path, "r") as file_handle:
            return file_handle.read()

    def _ensure_client(self) -> Any:
        if self.client is not None:
            return self.client

        if not self.api_key:
            if self.provider == "claude":
                raise TranslationError(
                    "Claude provider requires SAB_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY."
                )
            raise TranslationError(
                "Gemini provider requires SAB_GEMINI_API_KEY, GEMINI_API_KEY, or GOOGLE_API_KEY."
            )

        if self.provider == "claude":
            anthropic_module = importlib.import_module("anthropic")
            self.client = anthropic_module.Anthropic(api_key=self.api_key)
            return self.client

        genai_module = importlib.import_module("google.genai")
        self.client = genai_module.Client(api_key=self.api_key)
        return self.client

    def _build_prompt(self, prompt: str, context: SpreadsheetContext) -> str:
        return f"User Prompt: {prompt}\n\n{context.to_prompt_string()}"

    def _generate_claude(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        client = self._ensure_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=system_prompt,
            messages=messages,
        )
        return _extract_text_response(response)

    def _generate_gemini(self, system_prompt: str, contents: str) -> str:
        client = self._ensure_client()
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
            contents=contents,
            config=config,
        )
        return _extract_text_response(response)

    def translate(self, prompt: str, context: SpreadsheetContext) -> str:
        """
        Translates a user prompt + spreadsheet context into a raw blueprint JSON string.
        Implements auto-correction retry on validation failure.
        """
        if not self.api_key and self.client is None:
            if self.provider == "claude":
                raise TranslationError(
                    "Claude provider requires SAB_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY."
                )
            raise TranslationError(
                "Gemini provider requires SAB_GEMINI_API_KEY, GEMINI_API_KEY, or GOOGLE_API_KEY."
            )

        system_prompt = self._get_system_prompt()
        base_prompt = self._build_prompt(prompt, context)
        validator = BlueprintValidator()
        max_retries = 2
        attempt = 0
        raw_json = ""
        correction_note = ""

        while attempt <= max_retries:
            try:
                if self.provider == "claude":
                    messages: list[dict[str, str]] = [{"role": "user", "content": base_prompt}]
                    if correction_note:
                        messages.extend(
                            [
                                {"role": "assistant", "content": raw_json or "Error: Empty response"},
                                {
                                    "role": "user",
                                    "content": correction_note,
                                },
                            ]
                        )
                    raw_json = self._generate_claude(system_prompt, messages)
                else:
                    contents = base_prompt
                    if correction_note:
                        contents = (
                            f"{base_prompt}\n\nPrevious output:\n{raw_json or 'Error: Empty response'}\n\n"
                            f"Validation error:\n{correction_note}"
                        )
                    raw_json = self._generate_gemini(system_prompt, contents)

                raw_json = _strip_code_fences(raw_json)
                validator.validate(raw_json)
                return raw_json

            except Exception as exc:
                attempt += 1
                if attempt > max_retries:
                    raise TranslationError(
                        f"Failed to translate and validate blueprint after {max_retries} retries. Error: {exc}"
                    ) from exc

                correction_note = (
                    f"The output failed validation with the following error:\n{exc}\n\n"
                    "Please correct the JSON blueprint to comply with the schema and rules. "
                    "Do not include any explanation or markdown formatting, output raw JSON only."
                )

        raise TranslationError("Translation failed for unknown reasons during retry loop.")
