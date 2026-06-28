"""
tests/test_schemas.py — Comprehensive tests for AppSpec and Blueprint schemas.

Covers:
  - Valid instantiation of every model
  - Invalid instantiation (missing required fields, wrong types, bad enums)
  - Round-trip JSON serialization
  - Edge cases (empty sections, unicode, field constraints)
"""


import pytest
from pydantic import ValidationError

from core.app_spec import (
    ActionSpec,
    AppSpec,
    AppType,
    DesignPreferences,
    FieldSpec,
    FieldType,
    KPISpec,
    SectionSpec,
    SectionType,
)
from core.blueprint import AppType as BlueprintAppType
from core.blueprint import (
    Blueprint,
    BorderStyle,
    Cell,
    CellStyle,
    ConditionalFormat,
    Event,
    HAlign,
    MergeConfig,
    Meta,
    NamedRange,
    Region,
    RegionType,
    Validation,
    VAlign,
)

# ═══════════════════════════════════════════════════════════════════════════
# AppSpec schema tests
# ═══════════════════════════════════════════════════════════════════════════


class TestFieldSpec:
    """Tests for the FieldSpec model."""

    def test_valid_text_field(self) -> None:
        field = FieldSpec(name="Customer Name", field_type=FieldType.TEXT)
        assert field.name == "Customer Name"
        assert field.field_type == FieldType.TEXT
        assert field.options is None
        assert field.default_value is None

    def test_valid_dropdown_with_options(self) -> None:
        field = FieldSpec(
            name="Payment Method",
            field_type=FieldType.DROPDOWN,
            options=["Cash", "Card", "Mobile"],
            default_value="Cash",
        )
        assert field.options == ["Cash", "Card", "Mobile"]
        assert field.default_value == "Cash"

    def test_dropdown_without_options_fails(self) -> None:
        with pytest.raises(ValidationError, match="Dropdown fields must have at least one option"):
            FieldSpec(name="Method", field_type=FieldType.DROPDOWN, options=None)

    def test_dropdown_with_empty_options_fails(self) -> None:
        with pytest.raises(ValidationError, match="Dropdown fields must have at least one option"):
            FieldSpec(name="Method", field_type=FieldType.DROPDOWN, options=[])

    def test_valid_formula_field(self) -> None:
        field = FieldSpec(
            name="Subtotal",
            field_type=FieldType.FORMULA,
            formula="=quantity * unit_price",
            format_hint="currency",
        )
        assert field.formula == "=quantity * unit_price"
        assert field.format_hint == "currency"

    def test_valid_currency_field_with_validation(self) -> None:
        field = FieldSpec(
            name="Price",
            field_type=FieldType.CURRENCY,
            default_value=0.00,
            validation_rule=">=0",
        )
        assert field.validation_rule == ">=0"

    def test_empty_name_fails(self) -> None:
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            FieldSpec(name="", field_type=FieldType.TEXT)

    def test_missing_name_fails(self) -> None:
        with pytest.raises(ValidationError):
            FieldSpec(field_type=FieldType.TEXT)  # type: ignore[call-arg]

    def test_invalid_field_type_fails(self) -> None:
        with pytest.raises(ValidationError):
            FieldSpec(name="Test", field_type="invalid_type")  # type: ignore[arg-type]

    def test_all_field_types_valid(self) -> None:
        for ft in FieldType:
            kwargs: dict = {"name": f"Field {ft.value}", "field_type": ft}
            if ft == FieldType.DROPDOWN:
                kwargs["options"] = ["A", "B"]
            field = FieldSpec(**kwargs)
            assert field.field_type == ft

    def test_unicode_field_name(self) -> None:
        field = FieldSpec(name="日本語フィールド", field_type=FieldType.TEXT)
        assert field.name == "日本語フィールド"


class TestSectionSpec:
    """Tests for the SectionSpec model."""

    def test_valid_section(self) -> None:
        section = SectionSpec(
            section_id="order_items",
            title="Order Items",
            section_type=SectionType.DATA_TABLE,
            fields=[FieldSpec(name="Product", field_type=FieldType.TEXT)],
            repeatable=True,
            repeat_count=10,
        )
        assert section.section_id == "order_items"
        assert section.repeatable is True
        assert section.repeat_count == 10

    def test_default_repeat_count(self) -> None:
        section = SectionSpec(
            section_id="items",
            title="Items",
            section_type=SectionType.DATA_TABLE,
            fields=[FieldSpec(name="Item", field_type=FieldType.TEXT)],
        )
        assert section.repeatable is False
        assert section.repeat_count == 5

    def test_invalid_section_id_uppercase(self) -> None:
        with pytest.raises(ValidationError, match="section_id must be lowercase"):
            SectionSpec(
                section_id="OrderItems",
                title="Items",
                section_type=SectionType.DATA_TABLE,
                fields=[FieldSpec(name="Item", field_type=FieldType.TEXT)],
            )

    def test_invalid_section_id_starts_with_number(self) -> None:
        with pytest.raises(ValidationError, match="section_id must be lowercase"):
            SectionSpec(
                section_id="1items",
                title="Items",
                section_type=SectionType.DATA_TABLE,
                fields=[FieldSpec(name="Item", field_type=FieldType.TEXT)],
            )

    def test_empty_fields_fails(self) -> None:
        with pytest.raises(ValidationError, match="too_short"):
            SectionSpec(
                section_id="empty",
                title="Empty",
                section_type=SectionType.INPUT_FORM,
                fields=[],
            )

    def test_repeat_count_bounds(self) -> None:
        with pytest.raises(ValidationError):
            SectionSpec(
                section_id="items",
                title="Items",
                section_type=SectionType.DATA_TABLE,
                fields=[FieldSpec(name="Item", field_type=FieldType.TEXT)],
                repeat_count=0,
            )

        with pytest.raises(ValidationError):
            SectionSpec(
                section_id="items",
                title="Items",
                section_type=SectionType.DATA_TABLE,
                fields=[FieldSpec(name="Item", field_type=FieldType.TEXT)],
                repeat_count=101,
            )

    def test_all_section_types(self) -> None:
        for st in SectionType:
            section = SectionSpec(
                section_id=f"section_{st.value}",
                title=f"Section {st.value}",
                section_type=st,
                fields=[FieldSpec(name="Field", field_type=FieldType.TEXT)],
            )
            assert section.section_type == st


class TestKPISpec:
    """Tests for the KPISpec model."""

    def test_valid_kpi(self) -> None:
        kpi = KPISpec(
            label="Total Revenue",
            formula="SUM(line_items.subtotal)",
            format_hint="currency",
        )
        assert kpi.label == "Total Revenue"
        assert kpi.format_hint == "currency"

    def test_kpi_without_format(self) -> None:
        kpi = KPISpec(label="Count", formula="COUNT(orders)")
        assert kpi.format_hint is None

    def test_empty_label_fails(self) -> None:
        with pytest.raises(ValidationError):
            KPISpec(label="", formula="SUM(x)")

    def test_empty_formula_fails(self) -> None:
        with pytest.raises(ValidationError):
            KPISpec(label="Total", formula="")


class TestActionSpec:
    """Tests for the ActionSpec model."""

    def test_valid_action(self) -> None:
        action = ActionSpec(
            label="Submit Order",
            action_id="submit_order",
            style_hint="primary",
        )
        assert action.label == "Submit Order"
        assert action.action_id == "submit_order"
        assert action.style_hint == "primary"

    def test_action_without_style(self) -> None:
        action = ActionSpec(label="Reset", action_id="reset_form")
        assert action.style_hint is None

    def test_empty_action_id_fails(self) -> None:
        with pytest.raises(ValidationError):
            ActionSpec(label="Click", action_id="")


class TestDesignPreferences:
    """Tests for the DesignPreferences model."""

    def test_defaults(self) -> None:
        design = DesignPreferences()
        assert design.palette is None
        assert design.font is None
        assert design.emoji_enabled is True
        assert design.style_preset is None

    def test_full_preferences(self) -> None:
        design = DesignPreferences(
            palette="ocean",
            font="modern",
            emoji_enabled=False,
            style_preset="professional",
        )
        assert design.palette == "ocean"
        assert design.emoji_enabled is False


class TestAppSpec:
    """Tests for the top-level AppSpec model."""

    @pytest.fixture
    def minimal_app_spec(self) -> AppSpec:
        return AppSpec(
            app_type=AppType.POS,
            title="Simple POS",
            description="A basic point-of-sale terminal.",
            sections=[
                SectionSpec(
                    section_id="header",
                    title="POS Header",
                    section_type=SectionType.HEADER,
                    fields=[FieldSpec(name="Store Name", field_type=FieldType.LABEL)],
                ),
            ],
        )

    @pytest.fixture
    def full_app_spec(self) -> AppSpec:
        return AppSpec(
            app_type=AppType.INVOICE,
            title="Invoice Generator",
            description="Generate professional invoices with tax calculations.",
            sections=[
                SectionSpec(
                    section_id="header",
                    title="Invoice Header",
                    section_type=SectionType.HEADER,
                    fields=[
                        FieldSpec(name="Company Name", field_type=FieldType.LABEL),
                        FieldSpec(name="Invoice Number", field_type=FieldType.TEXT),
                        FieldSpec(name="Date", field_type=FieldType.DATE),
                    ],
                ),
                SectionSpec(
                    section_id="client_info",
                    title="Client Information",
                    section_type=SectionType.INPUT_FORM,
                    fields=[
                        FieldSpec(name="Client Name", field_type=FieldType.TEXT),
                        FieldSpec(name="Client Email", field_type=FieldType.TEXT),
                    ],
                ),
                SectionSpec(
                    section_id="line_items",
                    title="Line Items",
                    section_type=SectionType.DATA_TABLE,
                    fields=[
                        FieldSpec(name="Description", field_type=FieldType.TEXT),
                        FieldSpec(
                            name="Quantity",
                            field_type=FieldType.NUMBER,
                            default_value=1,
                            validation_rule=">=1",
                        ),
                        FieldSpec(
                            name="Unit Price",
                            field_type=FieldType.CURRENCY,
                            default_value=0.00,
                            validation_rule=">=0",
                        ),
                        FieldSpec(
                            name="Subtotal",
                            field_type=FieldType.FORMULA,
                            formula="=quantity * unit_price",
                            format_hint="currency",
                        ),
                    ],
                    repeatable=True,
                    repeat_count=10,
                ),
                SectionSpec(
                    section_id="summary",
                    title="Invoice Summary",
                    section_type=SectionType.SUMMARY,
                    fields=[
                        FieldSpec(
                            name="Grand Total",
                            field_type=FieldType.FORMULA,
                            formula="SUM(line_items.subtotal)",
                            format_hint="currency",
                        ),
                    ],
                ),
            ],
            kpis=[
                KPISpec(
                    label="Total Due",
                    formula="SUM(line_items.subtotal)",
                    format_hint="currency",
                ),
            ],
            actions=[
                ActionSpec(
                    label="Print Invoice",
                    action_id="print_invoice",
                    style_hint="primary",
                ),
            ],
            design=DesignPreferences(
                palette="corporate",
                font="classic",
                emoji_enabled=False,
                style_preset="professional",
            ),
        )

    def test_minimal_valid(self, minimal_app_spec: AppSpec) -> None:
        assert minimal_app_spec.app_type == AppType.POS
        assert len(minimal_app_spec.sections) == 1
        assert minimal_app_spec.kpis == []
        assert minimal_app_spec.actions == []

    def test_full_valid(self, full_app_spec: AppSpec) -> None:
        assert full_app_spec.app_type == AppType.INVOICE
        assert len(full_app_spec.sections) == 4
        assert len(full_app_spec.kpis) == 1
        assert len(full_app_spec.actions) == 1
        assert full_app_spec.design.palette == "corporate"

    def test_no_sections_fails(self) -> None:
        with pytest.raises(ValidationError, match="too_short"):
            AppSpec(
                app_type=AppType.OTHER,
                title="Empty App",
                description="No sections",
                sections=[],
            )

    def test_duplicate_section_ids_fails(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate section_id"):
            AppSpec(
                app_type=AppType.POS,
                title="Dup Test",
                description="Has duplicate section IDs",
                sections=[
                    SectionSpec(
                        section_id="header",
                        title="Header 1",
                        section_type=SectionType.HEADER,
                        fields=[FieldSpec(name="A", field_type=FieldType.LABEL)],
                    ),
                    SectionSpec(
                        section_id="header",
                        title="Header 2",
                        section_type=SectionType.HEADER,
                        fields=[FieldSpec(name="B", field_type=FieldType.LABEL)],
                    ),
                ],
            )

    def test_title_too_long_fails(self) -> None:
        with pytest.raises(ValidationError):
            AppSpec(
                app_type=AppType.OTHER,
                title="x" * 201,
                description="Valid",
                sections=[
                    SectionSpec(
                        section_id="s",
                        title="S",
                        section_type=SectionType.HEADER,
                        fields=[FieldSpec(name="F", field_type=FieldType.TEXT)],
                    )
                ],
            )

    def test_empty_title_fails(self) -> None:
        with pytest.raises(ValidationError):
            AppSpec(
                app_type=AppType.POS,
                title="",
                description="Valid",
                sections=[
                    SectionSpec(
                        section_id="s",
                        title="S",
                        section_type=SectionType.HEADER,
                        fields=[FieldSpec(name="F", field_type=FieldType.TEXT)],
                    )
                ],
            )

    def test_json_round_trip(self, full_app_spec: AppSpec) -> None:
        json_str = full_app_spec.model_dump_json()
        parsed = AppSpec.model_validate_json(json_str)
        assert parsed.title == full_app_spec.title
        assert len(parsed.sections) == len(full_app_spec.sections)
        assert parsed.design.palette == full_app_spec.design.palette

    def test_from_dict(self) -> None:
        data = {
            "app_type": "dashboard",
            "title": "Sales Dashboard",
            "description": "Real-time sales metrics",
            "sections": [
                {
                    "section_id": "metrics",
                    "title": "Key Metrics",
                    "section_type": "kpi_row",
                    "fields": [
                        {"name": "Revenue", "field_type": "currency"},
                        {"name": "Orders", "field_type": "number"},
                    ],
                },
            ],
            "kpis": [
                {"label": "Total Revenue", "formula": "SUM(metrics.revenue)"},
            ],
        }
        spec = AppSpec.model_validate(data)
        assert spec.app_type == AppType.DASHBOARD
        assert len(spec.sections[0].fields) == 2

    def test_all_app_types(self) -> None:
        for at in AppType:
            spec = AppSpec(
                app_type=at,
                title=f"Test {at.value}",
                description=f"A {at.value} app",
                sections=[
                    SectionSpec(
                        section_id="main",
                        title="Main",
                        section_type=SectionType.HEADER,
                        fields=[FieldSpec(name="F", field_type=FieldType.TEXT)],
                    )
                ],
            )
            assert spec.app_type == at


# ═══════════════════════════════════════════════════════════════════════════
# Blueprint schema tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCellStyle:
    """Tests for the CellStyle model."""

    def test_defaults(self) -> None:
        style = CellStyle()
        assert style.bg_color is None
        assert style.fg_color is None
        assert style.font_size == 10.0
        assert style.bold is False
        assert style.italic is False
        assert style.border_top == BorderStyle.NONE
        assert style.h_align == HAlign.LEFT
        assert style.v_align == VAlign.MIDDLE

    def test_full_style(self) -> None:
        style = CellStyle(
            bg_color="#1A237E",
            fg_color="#FFFFFF",
            font_size=14.0,
            bold=True,
            italic=True,
            border_top=BorderStyle.THIN,
            border_bottom=BorderStyle.DOUBLE,
            border_left=BorderStyle.MEDIUM,
            border_right=BorderStyle.DASHED,
            number_format="$#,##0.00",
            h_align=HAlign.CENTER,
            v_align=VAlign.TOP,
        )
        assert style.bg_color == "#1A237E"
        assert style.bold is True
        assert style.border_bottom == BorderStyle.DOUBLE

    def test_all_border_styles(self) -> None:
        for bs in BorderStyle:
            style = CellStyle(border_top=bs)
            assert style.border_top == bs

    def test_all_alignments(self) -> None:
        for h in HAlign:
            for v in VAlign:
                style = CellStyle(h_align=h, v_align=v)
                assert style.h_align == h
                assert style.v_align == v


class TestValidation:
    """Tests for the Validation model."""

    def test_list_validation(self) -> None:
        v = Validation(type="list", formula1="Cash,Card,Mobile")
        assert v.type == "list"
        assert v.allow_blank is True
        assert v.error_message is None

    def test_decimal_validation(self) -> None:
        v = Validation(
            type="decimal",
            formula1=">=0",
            allow_blank=False,
            error_message="Must be non-negative.",
        )
        assert v.allow_blank is False
        assert v.error_message == "Must be non-negative."

    def test_missing_type_fails(self) -> None:
        with pytest.raises(ValidationError):
            Validation(formula1="test")  # type: ignore[call-arg]

    def test_missing_formula1_fails(self) -> None:
        with pytest.raises(ValidationError):
            Validation(type="list")  # type: ignore[call-arg]


class TestCell:
    """Tests for the Cell model."""

    def test_value_cell(self) -> None:
        cell = Cell(cell_id="A1", value="Hello")
        assert cell.cell_id == "A1"
        assert cell.value == "Hello"
        assert cell.formula is None

    def test_formula_cell(self) -> None:
        cell = Cell(
            cell_id="B10",
            formula="=SUM(B2:B9)",
            style=CellStyle(bold=True, number_format="$#,##0.00"),
        )
        assert cell.formula == "=SUM(B2:B9)"
        assert cell.style is not None
        assert cell.style.bold is True

    def test_cell_with_validation(self) -> None:
        cell = Cell(
            cell_id="C5",
            value="Cash",
            validation=Validation(type="list", formula1="Cash,Card"),
        )
        assert cell.validation is not None
        assert cell.validation.type == "list"

    def test_cell_with_event(self) -> None:
        cell = Cell(
            cell_id="D5",
            value="Submit",
            event=Event(type="button", action="submit_order"),
        )
        assert cell.event is not None
        assert cell.event.action == "submit_order"

    def test_missing_cell_id_fails(self) -> None:
        with pytest.raises(ValidationError):
            Cell(value="test")  # type: ignore[call-arg]

    def test_numeric_value(self) -> None:
        cell = Cell(cell_id="B2", value=42.5)
        assert cell.value == 42.5

    def test_boolean_value(self) -> None:
        cell = Cell(cell_id="C3", value=True)
        assert cell.value is True


class TestRegion:
    """Tests for the Region model."""

    def test_valid_region(self) -> None:
        region = Region(
            region_id="header",
            type=RegionType.HEADER,
            anchor="A1",
            size=(2, 5),
            title="Main Header",
            cell_ids=["A1", "B1", "C1", "D1", "E1"],
        )
        assert region.region_id == "header"
        assert region.size == (2, 5)

    def test_all_region_types(self) -> None:
        for rt in RegionType:
            region = Region(
                region_id=f"region_{rt.value}",
                type=rt,
                anchor="A1",
                size=(1, 1),
                cell_ids=["A1"],
            )
            assert region.type == rt

    def test_missing_cell_ids_fails(self) -> None:
        with pytest.raises(ValidationError):
            Region(
                region_id="test",
                type=RegionType.HEADER,
                anchor="A1",
                size=(1, 1),
            )  # type: ignore[call-arg]


class TestMeta:
    """Tests for the Meta model."""

    def test_minimal_meta(self) -> None:
        meta = Meta(
            app_type=BlueprintAppType.POS,
            title="POS",
            description="Point of Sale",
        )
        assert meta.author == "SAB Engine"
        assert meta.version == "1.0.0"
        assert meta.frozen_rows == 0
        assert meta.hide_gridlines is False
        assert meta.col_widths == {}

    def test_full_meta(self) -> None:
        meta = Meta(
            app_type=BlueprintAppType.DASHBOARD,
            title="Sales Dashboard",
            description="Revenue tracking",
            frozen_rows=2,
            frozen_cols=1,
            hide_gridlines=True,
            col_widths={"A": 15.0, "B": 20.0},
            row_heights={1: 25.0, 2: 30.0},
        )
        assert meta.frozen_rows == 2
        assert meta.col_widths["A"] == 15.0


class TestConditionalFormat:
    """Tests for the ConditionalFormat model."""

    def test_valid_conditional_format(self) -> None:
        cf = ConditionalFormat(
            range="B2:B20",
            rule_type="cell_value",
            operator="greaterThan",
            formula="1000",
            style=CellStyle(bg_color="#C8E6C9", bold=True),
            priority=1,
        )
        assert cf.range == "B2:B20"
        assert cf.rule_type == "cell_value"
        assert cf.style is not None
        assert cf.style.bg_color == "#C8E6C9"

    def test_color_scale(self) -> None:
        cf = ConditionalFormat(
            range="C2:C50",
            rule_type="color_scale",
        )
        assert cf.operator is None
        assert cf.style is None
        assert cf.priority == 1


class TestBlueprint:
    """Tests for the top-level Blueprint model."""

    @pytest.fixture
    def minimal_blueprint(self) -> Blueprint:
        return Blueprint(
            meta=Meta(
                app_type=BlueprintAppType.OTHER,
                title="Minimal",
                description="Minimal blueprint",
            ),
            regions=[
                Region(
                    region_id="main",
                    type=RegionType.HEADER,
                    anchor="A1",
                    size=(1, 1),
                    cell_ids=["A1"],
                ),
            ],
            cells=[Cell(cell_id="A1", value="Hello")],
        )

    def test_minimal_valid(self, minimal_blueprint: Blueprint) -> None:
        assert minimal_blueprint.meta.title == "Minimal"
        assert len(minimal_blueprint.cells) == 1
        assert minimal_blueprint.merges == []
        assert minimal_blueprint.named_ranges == []
        assert minimal_blueprint.conditional_formats == []

    def test_with_merges_and_named_ranges(self) -> None:
        bp = Blueprint(
            meta=Meta(
                app_type=BlueprintAppType.INVOICE,
                title="Invoice",
                description="Test",
            ),
            regions=[
                Region(
                    region_id="header",
                    type=RegionType.HEADER,
                    anchor="A1",
                    size=(2, 3),
                    cell_ids=["A1"],
                ),
            ],
            cells=[Cell(cell_id="A1", value="Invoice")],
            merges=[MergeConfig(range="A1:C2")],
            named_ranges=[NamedRange(name="Title", range="A1")],
            conditional_formats=[
                ConditionalFormat(range="B5:B20", rule_type="data_bar"),
            ],
        )
        assert len(bp.merges) == 1
        assert bp.merges[0].range == "A1:C2"
        assert bp.named_ranges[0].name == "Title"
        assert len(bp.conditional_formats) == 1

    def test_json_round_trip(self, minimal_blueprint: Blueprint) -> None:
        json_str = minimal_blueprint.model_dump_json()
        parsed = Blueprint.model_validate_json(json_str)
        assert parsed.meta.title == minimal_blueprint.meta.title
        assert len(parsed.cells) == len(minimal_blueprint.cells)

    def test_fixture_blueprints_valid(self) -> None:
        """Validate all 3 fixture JSON files parse as valid Blueprints."""
        import os

        fixtures_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fixtures"
        )
        fixture_files = [
            "pos_blueprint.json",
            "dashboard_blueprint.json",
            "invoice_blueprint.json",
        ]
        for filename in fixture_files:
            filepath = os.path.join(fixtures_dir, filename)
            with open(filepath) as f:
                raw = f.read()
            bp = Blueprint.model_validate_json(raw)
            assert bp.meta.title
            assert len(bp.cells) > 0
            assert len(bp.regions) > 0

    def test_missing_meta_fails(self) -> None:
        with pytest.raises(ValidationError):
            Blueprint(
                regions=[],
                cells=[],
            )  # type: ignore[call-arg]

    def test_empty_regions_valid(self) -> None:
        """Empty regions list is technically valid at the schema level.
        Constraint checkers may reject it, but the model allows it."""
        bp = Blueprint(
            meta=Meta(
                app_type=BlueprintAppType.OTHER,
                title="Empty",
                description="No regions",
            ),
            regions=[],
            cells=[],
        )
        assert bp.regions == []
