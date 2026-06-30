"""Tests for core/pipeline.py orchestrator."""
from unittest.mock import MagicMock, patch

import pytest

from core.pipeline import PipelineError, PipelineResult, run

POS_SPEC_JSON = """{
  "app_type": "pos",
  "title": "Point of Sale (POS) Terminal",
  "description": "A Point of Sale application",
  "sections": [
    {
      "section_id": "details",
      "title": "Transaction Details",
      "section_type": "input_form",
      "fields": [
        {"name": "Product", "field_type": "dropdown", "options": ["Coffee", "Tea"]},
        {"name": "Quantity", "field_type": "number", "default_value": 1, "validation_rule": ">=1"},
        {"name": "Price", "field_type": "currency", "default_value": 2.50},
        {"name": "Total", "field_type": "formula", "formula": "=Quantity * Price"}
      ]
    }
  ]
}"""


def test_pipeline_validate_only():
    """validate_only=True should return a PipelineResult without rendering."""
    with patch("core.pipeline.AITranslator") as MockTranslator:
        instance = MockTranslator.return_value
        instance.translate.return_value = POS_SPEC_JSON

        result = run(
            prompt="POS terminal",
            api_key="test-key",
            validate_only=True,
        )

    assert isinstance(result, PipelineResult)
    assert result.blueprint is not None
    assert result.blueprint.meta.title == "Point of Sale (POS) Terminal"
    assert result.rendered is False
    assert result.raw_json == POS_SPEC_JSON


def test_pipeline_render_uno():
    """UNO adapter path should call adapter.render() with the blueprint."""
    with (
        patch("core.pipeline.AITranslator") as MockTranslator,
        patch("core.pipeline.UNOAdapter") as MockUNO,
    ):
        MockTranslator.return_value.translate.return_value = POS_SPEC_JSON

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


def test_pipeline_officejs_no_render():
    """Office.js adapter path should NOT render server-side."""
    with patch("core.pipeline.AITranslator") as MockTranslator:
        MockTranslator.return_value.translate.return_value = POS_SPEC_JSON

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
    """Invalid JSON or semantic layout failure should surface as PipelineError."""
    with patch("core.pipeline.AITranslator") as MockTranslator:
        MockTranslator.return_value.translate.return_value = '{"bad": "json"}'

        with pytest.raises(PipelineError, match="Failed to parse AI output as AppSpec JSON"):
            run(prompt="fail", api_key="test-key")


def test_pipeline_unknown_adapter():
    """Unknown adapter names should raise PipelineError."""
    with patch("core.pipeline.AITranslator") as MockTranslator:
        MockTranslator.return_value.translate.return_value = POS_SPEC_JSON

        with pytest.raises(PipelineError, match="Unknown adapter"):
            run(prompt="POS", api_key="test-key", adapter_name="google_sheets")
