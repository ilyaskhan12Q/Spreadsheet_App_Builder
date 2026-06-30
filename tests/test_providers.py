"""Tests for AI provider integrations and the provider factory."""
from unittest.mock import MagicMock

import pytest

from core.ai.providers.claude_provider import ClaudeProvider
from core.ai.providers.factory import get_provider
from core.ai.providers.gemini_provider import GeminiProvider
from core.ai.providers.openai_provider import OpenAIProvider


def test_factory_resolves_providers():
    claude = get_provider("claude", api_key="fake", model="claude-sonnet")
    assert isinstance(claude, ClaudeProvider)
    assert claude.api_key == "fake"
    assert claude.model == "claude-sonnet"

    gemini = get_provider("gemini", api_key="fake", model="gemini-2.5")
    assert isinstance(gemini, GeminiProvider)

    openai = get_provider("openai", api_key="fake", model="gpt-4o")
    assert isinstance(openai, OpenAIProvider)


def test_factory_raises_value_error_for_invalid_provider():
    with pytest.raises(ValueError, match="Unsupported provider"):
        get_provider("invalid_provider", api_key="fake", model="fake")  # type: ignore[arg-type]


def test_claude_provider_generate():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Claude response text"
    mock_client.messages.create.return_value = mock_response

    provider = ClaudeProvider(api_key="fake", model="claude-sonnet", client=mock_client)
    res = provider.generate("System", "User prompt")

    assert res == "Claude response text"
    mock_client.messages.create.assert_called_once_with(
        model="claude-sonnet",
        max_tokens=4000,
        system="System",
        messages=[{"role": "user", "content": "User prompt"}],
    )


def test_gemini_provider_generate():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Gemini response text"
    mock_client.models.generate_content.return_value = mock_response

    provider = GeminiProvider(api_key="fake", model="gemini-2.5", client=mock_client)
    res = provider.generate("System instruction", "User prompt")

    assert res == "Gemini response text"
    mock_client.models.generate_content.assert_called_once()
    # Check calling arguments
    call_args = mock_client.models.generate_content.call_args
    assert call_args[1]["model"] == "gemini-2.5"
    assert call_args[1]["contents"] == "User prompt"


def test_openai_provider_generate():
    mock_client = MagicMock()
    mock_response = MagicMock()

    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "OpenAI response text"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    mock_client.chat.completions.create.return_value = mock_response

    provider = OpenAIProvider(api_key="fake", model="gpt-4o", client=mock_client)
    res = provider.generate("System instructions", "User prompt")

    assert res == "OpenAI response text"
    mock_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "System instructions"},
            {"role": "user", "content": "User prompt"},
        ],
        response_format={"type": "json_object"},
    )
