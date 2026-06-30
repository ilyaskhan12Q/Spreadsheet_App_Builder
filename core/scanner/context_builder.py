import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpreadsheetContext:
    used_range: str = "A1"
    headers: list[str] = field(default_factory=list)
    data_sample: list[dict[str, Any]] = field(default_factory=list)
    named_ranges: dict[str, str] = field(default_factory=dict)
    existing_styles: dict[str, Any] = field(default_factory=dict)
    sheet_names: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpreadsheetContext":
        """
        Build a SpreadsheetContext from a dictionary, ensuring type alignment.
        """
        return cls(
            used_range=data.get("used_range", "A1"),
            headers=data.get("headers", []),
            data_sample=data.get("data_sample", []),
            named_ranges=data.get("named_ranges", {}),
            existing_styles=data.get("existing_styles", {}),
            sheet_names=data.get("sheet_names", [])
        )

    def to_prompt_string(self) -> str:
        """
        Serializes context information for embedding into the LLM system/user prompts.
        """
        lines = [
            "### SPREADSHEET CONTEXT INFO ###",
            f"Active sheet used range: {self.used_range}",
            f"Sheet names: {', '.join(self.sheet_names) if self.sheet_names else 'None'}",
            "Headers detected:",
            f"  {json.dumps(self.headers)}",
            "Data sample preview:",
            json.dumps(self.data_sample, indent=2),
            "Named Ranges:",
            json.dumps(self.named_ranges, indent=2),
            "Existing Styles Summary:",
            json.dumps(self.existing_styles, indent=2),
            "###############################"
        ]
        return "\n".join(lines)


class ContextScanner:
    """
    Scans the active spreadsheet state (LibreOffice or workbook payload)
    and constructs a SpreadsheetContext for AI provider prompt injection.
    """
    def build_context(self, spreadsheet_handle: Any = None) -> SpreadsheetContext:
        # If a handle is provided (e.g. LibreOffice document or JSON payload),
        # we can dynamically extract sheet names, headers, etc.
        # Currently returns a clean default context.
        if not spreadsheet_handle:
            return SpreadsheetContext()

        # Optional parsing/extraction logic could go here
        return SpreadsheetContext()
