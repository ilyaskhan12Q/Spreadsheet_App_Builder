"""core.ai.providers — Multi-provider AI layer (Gemini, Claude, OpenAI)."""
from core.ai.providers.base import BaseProvider
from core.ai.providers.factory import get_provider

__all__ = ["BaseProvider", "get_provider"]
