"""core/ai/providers/base.py — Abstract Base Class for AI Providers."""
import abc


class BaseProvider(abc.ABC):
    """
    Unified interface for AI API clients (Claude, Gemini, OpenAI).
    """

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abc.abstractmethod
    def generate(
        self,
        system_prompt: str,
        contents: str,
        message_history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Send system prompt and contents to the AI provider and return the raw text response.

        Parameters
        ----------
        system_prompt : str
            The system instructions.
        contents : str
            The user prompt and context string.
        message_history : Optional[list[dict[str, str]]]
            Optional multi-turn conversation messages list, e.g. for correction retries.
            Formatted as [{"role": "user"|"assistant", "content": "..."}].

        Returns
        -------
        str
            Raw string returned by the provider.
        """
        pass
