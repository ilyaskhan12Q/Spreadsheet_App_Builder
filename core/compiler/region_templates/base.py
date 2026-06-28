"""
core/compiler/region_templates/base.py — Shared template utilities.

Provides coordinate helpers, field registry for formula resolution,
formula injection prevention, and common cell-building helpers that
all region templates share.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.app_spec import FieldSpec, FieldType, SectionSpec
from core.blueprint import (
    BorderStyle,
    Cell,
    CellStyle,
    HAlign,
    MergeConfig,
    Region,
    RegionType,
    VAlign,
    Validation,
)
from core.compiler.design_tokens import ResolvedTokens, resolve_format_hint


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

def col_letter(n: int) -> str:
    """Convert 1-based column index to A1-style column letters.

    Args:
        n: 1-based column index (1=A, 26=Z, 27=AA, ...).

    Returns:
        Column letter string.

    Raises:
        ValueError: If n < 1.
    """
    if n < 1:
        raise ValueError(f"Column index must be >= 1, got {n}")
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def cell_ref(row: int, col: int) -> str:
    """Convert (row, col) to A1 notation.

    Args:
        row: 1-based row number.
        col: 1-based column number.

    Returns:
        Cell reference string like "A1", "C15".
    """
    return f"{col_letter(col)}{row}"


def cell_range(r1: int, c1: int, r2: int, c2: int) -> str:
    """Convert two (row, col) pairs to a range string.

    Args:
        r1, c1: Top-left cell (1-based).
        r2, c2: Bottom-right cell (1-based).

    Returns:
        Range string like "A1:C5".
    """
    return f"{cell_ref(r1, c1)}:{cell_ref(r2, c2)}"


# ---------------------------------------------------------------------------
# Formula injection prevention
# ---------------------------------------------------------------------------

DANGEROUS_FUNCTIONS = frozenset({
    "HYPERLINK", "IMPORTXML", "IMPORTDATA", "IMPORTHTML",
    "IMPORTRANGE", "IMPORTFEED", "WEBSERVICE", "FILTERXML",
    "IMAGE", "CALL", "REGISTER.ID",
})

_DANGEROUS_PATTERN = re.compile(
    r"=\s*(" + "|".join(re.escape(f) for f in DANGEROUS_FUNCTIONS) + r")\s*\(",
    re.IGNORECASE,
)


class FormulaInjectionError(ValueError):
    """Raised when a formula contains a dangerous function."""


def check_formula_safe(formula: str) -> None:
    """Verify a formula does not contain injection-risk functions.

    Args:
        formula: The formula string to check.

    Raises:
        FormulaInjectionError: If a dangerous function is detected.
    """
    if _DANGEROUS_PATTERN.search(formula):
        raise FormulaInjectionError(
            f"Formula contains a dangerous function: {formula!r}"
        )


# ---------------------------------------------------------------------------
# Field registry — maps semantic field names to cell coordinates
# ---------------------------------------------------------------------------

@dataclass
class FieldEntry:
    """Registry entry for a single field placement."""

    section_id: str
    field_name: str
    cell_ids: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        """Canonical lookup key: section_id.field_name (lowercased)."""
        return f"{self.section_id}.{self.field_name}".lower()

    @property
    def single_cell(self) -> str:
        """Return the single cell ref (for non-repeatable fields)."""
        if not self.cell_ids:
            raise ValueError(f"No cells registered for {self.key}")
        return self.cell_ids[0]

    @property
    def range_str(self) -> str:
        """Return the full range string (for repeatable fields)."""
        if not self.cell_ids:
            raise ValueError(f"No cells registered for {self.key}")
        if len(self.cell_ids) == 1:
            return self.cell_ids[0]
        return f"{self.cell_ids[0]}:{self.cell_ids[-1]}"


class FieldRegistry:
    """Tracks field→cell_id mappings for formula resolution.

    Populated during template compilation as sections are placed on
    the grid. Consumed by the formula resolver to convert semantic
    references to A1-notation cell references.
    """

    def __init__(self) -> None:
        self._entries: dict[str, FieldEntry] = {}

    def register(
        self, section_id: str, field_name: str, cell_id: str
    ) -> None:
        """Register a cell_id for a field.

        Args:
            section_id: The section this field belongs to.
            field_name: The field name.
            cell_id: The A1 cell reference.
        """
        key = f"{section_id}.{field_name}".lower()
        if key not in self._entries:
            self._entries[key] = FieldEntry(
                section_id=section_id, field_name=field_name
            )
        self._entries[key].cell_ids.append(cell_id)

    def get(self, key: str) -> FieldEntry | None:
        """Look up a field entry by its canonical key.

        Args:
            key: Lookup key like "line_items.subtotal" (case-insensitive).

        Returns:
            FieldEntry if found, None otherwise.
        """
        return self._entries.get(key.lower())

    def get_range(self, key: str) -> str | None:
        """Get the cell range string for a field.

        Args:
            key: Lookup key like "line_items.subtotal".

        Returns:
            Range string like "D11:D20", or None if not found.
        """
        entry = self.get(key)
        if entry is None:
            return None
        return entry.range_str

    def resolve_formula(
        self,
        semantic_formula: str,
        current_row: int | None = None,
        section_id: str | None = None,
    ) -> str:
        """Resolve a semantic formula to A1-notation cell references.

        Handles two patterns:
        1. Simple field references: `=quantity * unit_price`
           → resolves within the same section, same row
        2. Aggregation: `SUM(section.field)` or `SUM(line_items.subtotal)`
           → resolves to a range

        Args:
            semantic_formula: The semantic formula string.
            current_row: Current row for same-section field lookups.
            section_id: Current section for unqualified field names.

        Returns:
            Resolved formula with A1 cell references.

        Raises:
            FormulaInjectionError: If formula contains dangerous functions.
        """
        check_formula_safe(semantic_formula)

        formula = semantic_formula

        # Pattern 1: Aggregation — SUM(section.field), COUNT(section.field), etc
        agg_pattern = re.compile(
            r"(SUM|COUNT|AVERAGE|MIN|MAX|COUNTA)"
            r"\(([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\)",
            re.IGNORECASE,
        )
        for match in agg_pattern.finditer(formula):
            func_name = match.group(1)
            sec_id = match.group(2)
            fld_name = match.group(3)
            key = f"{sec_id}.{fld_name}"
            cell_range_str = self.get_range(key)
            if cell_range_str:
                formula = formula.replace(
                    match.group(0), f"{func_name}({cell_range_str})"
                )

        # Pattern 2: Simple field references within same section/row
        if section_id and current_row:
            # Find bare field names (not preceded by dot or letter)
            # Match words that could be field names
            field_name_pattern = re.compile(r"\b([a-z_][a-z0-9_]*)\b", re.IGNORECASE)
            # Collect replacements to avoid modifying during iteration
            replacements: list[tuple[str, str]] = []
            for match in field_name_pattern.finditer(formula):
                word = match.group(1)
                # Skip spreadsheet functions and operators
                if word.upper() in {
                    "SUM", "COUNT", "AVERAGE", "MIN", "MAX", "IF",
                    "COUNTA", "COUNTIF", "SUMIF", "AND", "OR", "NOT",
                    "TRUE", "FALSE", "ABS", "ROUND",
                }:
                    continue
                key = f"{section_id}.{word}"
                entry = self.get(key)
                if entry and entry.cell_ids:
                    # Find the cell in the current row
                    target = _find_cell_in_row(entry.cell_ids, current_row)
                    if not target and len(entry.cell_ids) == 1:
                        target = entry.cell_ids[0]
                    if target:
                        replacements.append((word, target))

            # Apply replacements (longest first to avoid partial matches)
            replacements.sort(key=lambda x: len(x[0]), reverse=True)
            for old, new in replacements:
                formula = re.sub(
                    rf"\b{re.escape(old)}\b", new, formula,
                    flags=re.IGNORECASE,
                )

        if formula and not formula.strip().startswith("="):
            formula = "=" + formula.strip()
        return formula


def _find_cell_in_row(cell_ids: list[str], row: int) -> str | None:
    """Find a cell reference in the given row from a list of cell_ids.

    Args:
        cell_ids: List of A1 cell references.
        row: The row number to find.

    Returns:
        The matching cell_id, or None.
    """
    row_str = str(row)
    for cid in cell_ids:
        # Extract row number from cell ref
        match = re.match(r"^[A-Z]+(\d+)$", cid)
        if match and match.group(1) == row_str:
            return cid
    return None


# ---------------------------------------------------------------------------
# Cell-building helpers
# ---------------------------------------------------------------------------

def make_style(
    tokens: ResolvedTokens,
    *,
    bg_color: str | None = None,
    fg_color: str | None = None,
    bold: bool = False,
    italic: bool = False,
    font_size: float | None = None,
    h_align: HAlign = HAlign.LEFT,
    v_align: VAlign = VAlign.MIDDLE,
    number_format: str | None = None,
    border: str | None = None,
) -> CellStyle:
    """Build a CellStyle using resolved tokens.

    Args:
        tokens: Resolved design tokens.
        bg_color: Override background color (hex).
        fg_color: Override foreground color (hex).
        bold: Bold text.
        italic: Italic text.
        font_size: Override font size.
        h_align: Horizontal alignment.
        v_align: Vertical alignment.
        number_format: Number format string.
        border: Border style to apply on all sides (or None).

    Returns:
        A CellStyle instance.
    """
    border_style = BorderStyle(border) if border else BorderStyle.NONE

    return CellStyle(
        bg_color=bg_color,
        fg_color=fg_color,
        font_size=font_size or tokens.font.base_size,
        bold=bold,
        italic=italic,
        border_top=border_style,
        border_bottom=border_style,
        border_left=border_style,
        border_right=border_style,
        number_format=number_format,
        h_align=h_align,
        v_align=v_align,
    )


def section_type_to_region_type(section_type: str) -> RegionType:
    """Map AppSpec SectionType to Blueprint RegionType.

    Args:
        section_type: The SectionType value string.

    Returns:
        Corresponding RegionType.
    """
    mapping: dict[str, RegionType] = {
        "header": RegionType.HEADER,
        "input_form": RegionType.INPUT,
        "data_table": RegionType.DATA_TABLE,
        "summary": RegionType.OUTPUT,
        "actions": RegionType.INPUT,
        "kpi_row": RegionType.KPI_CARD,
    }
    return mapping.get(section_type, RegionType.INPUT)


def field_type_to_format_hint(field_type: FieldType) -> str | None:
    """Infer a format hint from the field type when none is explicit.

    Args:
        field_type: The FieldType enum value.

    Returns:
        Format hint string or None.
    """
    mapping: dict[FieldType, str] = {
        FieldType.CURRENCY: "currency",
        FieldType.DATE: "date",
        FieldType.NUMBER: "number",
    }
    return mapping.get(field_type)


def build_validation(field_spec: FieldSpec) -> Validation | None:
    """Build a Validation object from a FieldSpec's constraints.

    Args:
        field_spec: The field specification.

    Returns:
        A Validation instance, or None if no validation needed.
    """
    if field_spec.field_type == FieldType.DROPDOWN and field_spec.options:
        return Validation(
            type="list",
            formula1=",".join(field_spec.options),
            allow_blank=False,
            error_message=f"Please select a valid {field_spec.name}.",
        )

    if field_spec.validation_rule:
        rule = field_spec.validation_rule.strip()
        if rule.lower() == "required":
            return Validation(
                type="text_length",
                formula1="1",
                allow_blank=False,
                error_message=f"{field_spec.name} is required.",
            )
        # Numeric constraints like ">=0", "<=100"
        if re.match(r"^[<>=!]+\s*[\d.]+$", rule):
            return Validation(
                type="decimal",
                formula1=rule,
                allow_blank=False,
                error_message=f"{field_spec.name} must satisfy: {rule}.",
            )

    return None
