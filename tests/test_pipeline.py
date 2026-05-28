"""Tests for core/pipeline.py orchestrator."""
import json
import os
import pytest
from unittest.mock import MagicMock, patch

from core.pipeline import run, PipelineError, PipelineResult


@pytest.fixture
def pos_json() -> str:
    fixture_path = os.path.join(
        os.path.dirname(__file__), "fixtures", "pos_blueprint.json"
    )
    with open(fixture_path) as f:
        return f.read()


def test_pipeline_validate_only(pos_json: str):
    """validate_only=True should return a PipelineResult without rendering."""
    with patch("core.pipeline.AITranslator") as MockTranslator:
        instance = MockTranslator.return_value
        instance.translate.return_value = pos_json

        result = run(
            prompt="POS terminal",
            api_key="test-key",
            validate_only=True,
        )

    assert isinstance(result, PipelineResult)
    assert result.blueprint is not None
    assert result.blueprint.meta.title == "Point of Sale (POS) Terminal"
    assert result.rendered is False
    assert result.raw_json == pos_json


def test_pipeline_render_uno(pos_json: str):
    """UNO adapter path should call adapter.render() with the blueprint."""
    with (
        patch("core.pipeline.AITranslator") as MockTranslator,
        patch("core.pipeline.UNOAdapter") as MockUNO,
    ):
        MockTranslator.return_value.translate.return_value = pos_json

        mock_doc = MagicMock()
        result = run(
            prompt="POS terminal",
            api_key="test-key",
            adapter_name="uno",
            spreadsheet_handle=mock_doc,
        )

    assert result.rendered is True
    MockUNO.return_value.render.assert_called_once()
    call_args = MockUNO.return_value.render.call_args
    assert call_args[0][0].meta.title == "Point of Sale (POS) Terminal"
    assert call_args[0][1] is mock_doc


def test_pipeline_officejs_no_render(pos_json: str):
    """Office.js adapter path should NOT render server-side."""
    with patch("core.pipeline.AITranslator") as MockTranslator:
        MockTranslator.return_value.translate.return_value = pos_json

        result = run(
            prompt="POS terminal",
            api_key="test-key",
            adapter_name="officejs",
        )

    assert result.rendered is False
    assert result.blueprint is not None


def test_pipeline_translation_failure():
    """Translation stage errors should surface as PipelineError."""
    with patch("core.pipeline.AITranslator") as MockTranslator:
        from core.ai.translator import TranslationError

        MockTranslator.return_value.translate.side_effect = TranslationError("boom")

        with pytest.raises(PipelineError, match="Translation stage failed"):
            run(prompt="fail", api_key="test-key")


def test_pipeline_validation_failure():
    """Invalid JSON should surface as PipelineError at validation stage."""
    with patch("core.pipeline.AITranslator") as MockTranslator:
        MockTranslator.return_value.translate.return_value = '{"bad": "json"}'

        with pytest.raises(PipelineError, match="Validation stage failed"):
            run(prompt="fail", api_key="test-key")


def test_pipeline_unknown_adapter(pos_json: str):
    """Unknown adapter names should raise PipelineError."""
    with patch("core.pipeline.AITranslator") as MockTranslator:
        MockTranslator.return_value.translate.return_value = pos_json

        with pytest.raises(PipelineError, match="Unknown adapter"):
            run(prompt="POS", api_key="test-key", adapter_name="google_sheets")
