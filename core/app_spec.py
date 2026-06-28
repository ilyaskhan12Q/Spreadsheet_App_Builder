"""
core/app_spec.py — Semantic App Spec schema.

This is the small, AI-friendly schema that describes WHAT an app needs
without specifying WHERE or HOW it looks. The AI provider outputs an
AppSpec; the deterministic Blueprint Compiler converts it into a full
Blueprint with exact cell coordinates, hex colors, and layout.

Design rules:
  - No cell coordinates (A1 notation) — the compiler assigns positions.
  - No hex color values — palette names and style hints only.
  - Formulas reference field names semantically, not cell refs.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AppType(StrEnum):
    """High-level category of spreadsheet application."""

    POS = "pos"
    DASHBOARD = "dashboard"
    INVOICE = "invoice"
    TRACKER = "tracker"
    OTHER = "other"


class FieldType(StrEnum):
    """The logical data type of a field in a section."""

    TEXT = "text"
    NUMBER = "number"
    CURRENCY = "currency"
    DATE = "date"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    FORMULA = "formula"
    LABEL = "label"
    BUTTON = "button"


class SectionType(StrEnum):
    """The role a section plays in the app layout."""

    HEADER = "header"
    INPUT_FORM = "input_form"
    DATA_TABLE = "data_table"
    SUMMARY = "summary"
    ACTIONS = "actions"
    KPI_ROW = "kpi_row"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class FieldSpec(BaseModel):
    """A single field inside a section.

    Fields describe inputs, labels, computed values, or buttons — the
    compiler decides where each one lands on the sheet.
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable field name, e.g. 'Product Name'.",
    )
    field_type: FieldType = Field(
        ...,
        description="Logical data type of this field.",
    )
    options: list[str] | None = Field(
        None,
        description="Dropdown options. Required when field_type is 'dropdown'.",
    )
    default_value: Any | None = Field(
        None,
        description="Default value shown when the app is first opened.",
    )
    formula: str | None = Field(
        None,
        description=(
            "Semantic formula referencing other field names, e.g. "
            "'=quantity * unit_price'. The compiler resolves to cell refs."
        ),
    )
    validation_rule: str | None = Field(
        None,
        description=(
            "Validation constraint, e.g. '>=0', 'required', '<=100'. "
            "The compiler translates to spreadsheet data validation."
        ),
    )
    format_hint: str | None = Field(
        None,
        description=(
            "Display format hint: 'currency', 'percentage', 'integer', "
            "'date', 'text'. The compiler maps to number_format strings."
        ),
    )

    @field_validator("options")
    @classmethod
    def dropdown_requires_options(cls, v: list[str] | None, info: Any) -> list[str] | None:
        """Ensure dropdown fields have at least one option."""
        field_type = info.data.get("field_type")
        if field_type == FieldType.DROPDOWN and (v is None or len(v) == 0):
            raise ValueError("Dropdown fields must have at least one option.")
        return v


class SectionSpec(BaseModel):
    """A logical section of the app (header, input form, table, etc.).

    The compiler maps each section to a Region in the Blueprint, choosing
    anchor position and size deterministically based on app_type templates.
    """

    section_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this section, e.g. 'line_items'.",
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Display title for the section, e.g. 'Order Items'.",
    )
    section_type: SectionType = Field(
        ...,
        description="The role this section plays in the layout.",
    )
    fields: list[FieldSpec] = Field(
        ...,
        min_length=1,
        description="Fields belonging to this section.",
    )
    repeatable: bool = Field(
        False,
        description=(
            "When True, the section represents a line-item table where "
            "multiple rows share the same field structure."
        ),
    )
    repeat_count: int = Field(
        5,
        ge=1,
        le=100,
        description=(
            "Number of pre-allocated rows when repeatable is True. "
            "Ignored when repeatable is False."
        ),
    )

    @field_validator("section_id")
    @classmethod
    def section_id_must_be_slug(cls, v: str) -> str:
        """Section IDs must be lowercase alphanumeric with underscores."""
        import re

        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                f"section_id must be lowercase alphanumeric with underscores, got '{v}'."
            )
        return v


class KPISpec(BaseModel):
    """A key performance indicator displayed prominently in the app."""

    label: str = Field(
        ...,
        min_length=1,
        description="Display label, e.g. 'Total Revenue'.",
    )
    formula: str = Field(
        ...,
        min_length=1,
        description=(
            "Semantic formula or aggregation referencing section/field names, "
            "e.g. 'SUM(line_items.subtotal)'. The compiler resolves to cell refs."
        ),
    )
    format_hint: str | None = Field(
        None,
        description="Display format: 'currency', 'percentage', 'number'.",
    )


class ActionSpec(BaseModel):
    """An interactive button or action trigger."""

    label: str = Field(
        ...,
        min_length=1,
        description="Button text, e.g. 'Submit Order'.",
    )
    action_id: str = Field(
        ...,
        min_length=1,
        description="Unique action identifier, e.g. 'submit_order'.",
    )
    style_hint: str | None = Field(
        None,
        description="Visual style hint: 'primary', 'secondary', 'danger'.",
    )


class DesignPreferences(BaseModel):
    """User's visual preferences — the compiler resolves these to concrete
    hex colors, fonts, and styling via Design Tokens."""

    palette: str | None = Field(
        None,
        description=(
            "Named color palette: 'ocean', 'sunset', 'forest', 'corporate', "
            "'monochrome'. None means auto-select based on app_type."
        ),
    )
    font: str | None = Field(
        None,
        description=(
            "Font preference: 'modern', 'classic', 'monospace'. "
            "None means use the default for the app_type."
        ),
    )
    emoji_enabled: bool = Field(
        True,
        description="Whether to include emoji decorations in headers/labels.",
    )
    style_preset: str | None = Field(
        None,
        description=(
            "Overall style preset: 'minimal', 'bold', 'professional', "
            "'playful'. Affects spacing, borders, and emphasis."
        ),
    )


# ---------------------------------------------------------------------------
# Top-level schema
# ---------------------------------------------------------------------------

class AppSpec(BaseModel):
    """Semantic specification for a spreadsheet application.

    This is the output target for the AI provider. It describes the app's
    purpose, structure, and design preferences without any spatial or
    color-specific information. The Blueprint Compiler converts an AppSpec
    into a full Blueprint deterministically.
    """

    app_type: AppType = Field(
        ...,
        description="High-level category of the spreadsheet app.",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Title of the spreadsheet application.",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Brief summary explaining what the app does.",
    )
    sections: list[SectionSpec] = Field(
        ...,
        min_length=1,
        description="Ordered list of logical sections making up the app.",
    )
    kpis: list[KPISpec] = Field(
        default_factory=list,
        description="Key performance indicators for dashboard-style apps.",
    )
    actions: list[ActionSpec] = Field(
        default_factory=list,
        description="Interactive buttons/actions in the app.",
    )
    design: DesignPreferences = Field(
        default_factory=DesignPreferences,  # type: ignore[arg-type]
        description="Visual design preferences resolved by the compiler.",
    )

    @field_validator("sections")
    @classmethod
    def unique_section_ids(cls, v: list[SectionSpec]) -> list[SectionSpec]:
        """All section IDs must be unique."""
        ids = [s.section_id for s in v]
        duplicates = [sid for sid in ids if ids.count(sid) > 1]
        if duplicates:
            raise ValueError(f"Duplicate section_id(s): {set(duplicates)}")
        return v
