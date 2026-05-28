import json
import os
import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from core.blueprint import Blueprint
from core.scanner.context_builder import SpreadsheetContext
from core.ai.translator import AITranslator, TranslationError, describe_provider_setup
from core.validator.schema import BlueprintValidator
from core.validator.constraint_checker import LayoutConflictError


@pytest.fixture
def fixtures_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "fixtures")


@pytest.fixture
def pos_json(fixtures_dir):
    with open(os.path.join(fixtures_dir, "pos_blueprint.json"), "r") as f:
        return f.read()


@pytest.fixture
def dashboard_json(fixtures_dir):
    with open(os.path.join(fixtures_dir, "dashboard_blueprint.json"), "r") as f:
        return f.read()


@pytest.fixture
def invoice_json(fixtures_dir):
    with open(os.path.join(fixtures_dir, "invoice_blueprint.json"), "r") as f:
        return f.read()


def test_validation_happy_path(pos_json, dashboard_json, invoice_json):
    validator = BlueprintValidator()
    
    # Test POS
    pos_bp = validator.validate(pos_json)
    assert isinstance(pos_bp, Blueprint)
    assert pos_bp.meta.title == "Point of Sale (POS) Terminal"
    
    # Test Dashboard
    dash_bp = validator.validate(dashboard_json)
    assert isinstance(dash_bp, Blueprint)
    assert dash_bp.meta.hide_gridlines is True
    
    # Test Invoice
    inv_bp = validator.validate(invoice_json)
    assert isinstance(inv_bp, Blueprint)
    assert len(inv_bp.merges) == 1


def test_bounds_conflict(pos_json):
    validator = BlueprintValidator()
    
    # Cell bounds conflict
    data = json.loads(pos_json)
    data["cells"][0]["cell_id"] = "AY100"  # Col 51, max_col is 50
    malformed_json = json.dumps(data)
    with pytest.raises(LayoutConflictError) as excinfo:
        validator.validate(malformed_json)
    assert "out of bounds" in str(excinfo.value)

    # Region bounds conflict
    data = json.loads(pos_json)
    data["regions"][0]["size"] = [1001, 5]  # Row 1001, max_row is 1000
    malformed_json = json.dumps(data)
    with pytest.raises(LayoutConflictError) as excinfo:
        validator.validate(malformed_json)
    assert "exceeds boundaries" in str(excinfo.value)


def test_merge_conflict(pos_json):
    validator = BlueprintValidator()
    data = json.loads(pos_json)
    # Add a merge range that overlaps with A1:E2 (e.g. B2:C3)
    data["merges"].append({"range": "B2:C3"})
    malformed_json = json.dumps(data)
    with pytest.raises(LayoutConflictError) as excinfo:
        validator.validate(malformed_json)
    assert "Overlap detected" in str(excinfo.value)


def test_formula_syntax_conflict(pos_json):
    validator = BlueprintValidator()
    data = json.loads(pos_json)
    # Change a formula to not start with =
    data["cells"][-1]["formula"] = "B6*B7"  # B10 in pos_blueprint.json (or last cell)
    # Ensure it's a cell with formula
    found = False
    for cell in data["cells"]:
        if cell.get("formula") is not None:
            cell["formula"] = "B6*B7"
            found = True
    assert found
    malformed_json = json.dumps(data)
    with pytest.raises(LayoutConflictError) as excinfo:
        validator.validate(malformed_json)
    assert "must start with" in str(excinfo.value)


def test_context_prompt_serialization():
    ctx = SpreadsheetContext.from_dict({
        "used_range": "A1:C10",
        "headers": ["Name", "Age", "Salary"],
        "data_sample": [{"Name": "Alice", "Age": 30, "Salary": 50000}],
        "named_ranges": {"TotalSalary": "C11"},
        "existing_styles": {},
        "sheet_names": ["Sheet1"]
    })
    prompt_str = ctx.to_prompt_string()
    assert "A1:C10" in prompt_str
    assert "TotalSalary" in prompt_str
    assert "Alice" in prompt_str


@patch("anthropic.Anthropic")
def test_translator_happy_path(mock_anthropic, pos_json):
    # Mock anthropic messages response
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=pos_json)]
    mock_client.messages.create.return_value = mock_message

    translator = AITranslator(api_key="fake-key")
    ctx = SpreadsheetContext()
    res = translator.translate("Create a POS system", ctx)
    
    assert res.strip() == pos_json.strip()
    mock_client.messages.create.assert_called_once()


@patch("anthropic.Anthropic")
def test_translator_retry_and_success(mock_anthropic, pos_json):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    # First call returns invalid JSON, second call returns valid POS JSON
    mock_message_invalid = MagicMock()
    mock_message_invalid.content = [MagicMock(text="INVALID_JSON_HERE")]
    
    mock_message_valid = MagicMock()
    mock_message_valid.content = [MagicMock(text=pos_json)]
    
    mock_client.messages.create.side_effect = [mock_message_invalid, mock_message_valid]

    translator = AITranslator(api_key="fake-key")
    ctx = SpreadsheetContext()
    res = translator.translate("Create POS", ctx)

    assert res.strip() == pos_json.strip()
    assert mock_client.messages.create.call_count == 2


@patch("anthropic.Anthropic")
def test_translator_max_retries_failure(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    # Repeatedly return invalid JSON
    mock_message_invalid = MagicMock()
    mock_message_invalid.content = [MagicMock(text="INVALID_JSON")]
    mock_client.messages.create.return_value = mock_message_invalid

    translator = AITranslator(api_key="fake-key")
    ctx = SpreadsheetContext()

    with pytest.raises(TranslationError) as excinfo:
        translator.translate("Create POS", ctx)
    
    assert "Failed to translate and validate blueprint after 2 retries" in str(excinfo.value)
    assert mock_client.messages.create.call_count == 3  # Initial + 2 retries = 3 calls


def test_translator_gemini_happy_path(pos_json):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = pos_json
    mock_client.models.generate_content.return_value = mock_response

    translator = AITranslator(provider="gemini", client=mock_client)
    ctx = SpreadsheetContext()
    res = translator.translate("Create a POS system", ctx)

    assert res.strip() == pos_json.strip()
    mock_client.models.generate_content.assert_called_once()


def test_describe_provider_setup(monkeypatch):
    monkeypatch.setenv("SAB_GEMINI_API_KEY", "test-gemini-key")
    assert describe_provider_setup("gemini") == "gemini configured via SAB_GEMINI_API_KEY"
    assert describe_provider_setup("claude", api_key="override-key") == "claude configured via explicit API key"
