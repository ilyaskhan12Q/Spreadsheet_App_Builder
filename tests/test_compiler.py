import pytest
from core.app_spec import (
    AppSpec,
    AppType,
    SectionSpec,
    SectionType,
    FieldSpec,
    FieldType,
    KPISpec,
    ActionSpec,
    DesignPreferences,
)
from core.blueprint import Blueprint, AppType as BlueprintAppType
from core.compiler.app_spec_to_blueprint import compile_app_spec
from core.compiler.region_templates.base import FormulaInjectionError
from core.validator.schema import BlueprintValidator


def test_compile_pos():
    spec = AppSpec(
        app_type=AppType.POS,
        title="POS App",
        description="A Point of Sale application",
        design=DesignPreferences(palette="ocean", font="modern", style_preset="bold", emoji_enabled=True),
        sections=[
            SectionSpec(
                section_id="details",
                title="Transaction Details",
                section_type=SectionType.INPUT_FORM,
                fields=[
                    FieldSpec(name="Product", field_type=FieldType.DROPDOWN, options=["Coffee", "Tea"]),
                    FieldSpec(name="Quantity", field_type=FieldType.NUMBER, default_value=1, validation_rule=">=1"),
                    FieldSpec(name="Price", field_type=FieldType.CURRENCY, default_value=2.50),
                    FieldSpec(name="Total", field_type=FieldType.FORMULA, formula="=Quantity * Price"),
                ],
            )
        ],
    )
    blueprint = compile_app_spec(spec)
    assert isinstance(blueprint, Blueprint)
    assert blueprint.meta.app_type == BlueprintAppType.POS
    assert blueprint.meta.title == "POS App"
    
    # Verify the formula got resolved to A1 reference
    # Quantity will be B6, Price will be B7, Total is formula in B8 which resolves to =B6 * B7
    total_cell = next(c for c in blueprint.cells if c.cell_id == "B8")
    assert total_cell.formula == "=B6 * B7"
    
    # Validate the generated blueprint using BlueprintValidator
    validator = BlueprintValidator()
    validated = validator.validate(blueprint.model_dump_json())
    assert validated.meta.title == "POS App"


def test_compile_dashboard():
    spec = AppSpec(
        app_type=AppType.DASHBOARD,
        title="Sales Dashboard",
        description="A Sales Dashboard",
        design=DesignPreferences(palette="sunset", font="modern", style_preset="minimal", emoji_enabled=False),
        sections=[
            SectionSpec(
                section_id="sales_table",
                title="Sales Data",
                section_type=SectionType.DATA_TABLE,
                repeatable=True,
                repeat_count=3,
                fields=[
                    FieldSpec(name="Date", field_type=FieldType.DATE),
                    FieldSpec(name="Amount", field_type=FieldType.CURRENCY),
                ],
            )
        ],
        kpis=[
            KPISpec(label="Total Sales", formula="SUM(sales_table.Amount)", format_hint="currency")
        ],
    )
    blueprint = compile_app_spec(spec)
    assert isinstance(blueprint, Blueprint)
    assert blueprint.meta.app_type == BlueprintAppType.DASHBOARD
    
    # sales_table fields: Date in col 1, Amount in col 2.
    # Header row is row 7.
    # Repeat count 3: rows 8, 9, 10.
    # Amount is col 2 (B). Range is B8:B10.
    # KPI formula should be =SUM(B8:B10)
    kpi_val_cell = next(c for c in blueprint.cells if c.cell_id == "B4")
    assert kpi_val_cell.formula == "=SUM(B8:B10)"
    
    # Validate the generated blueprint
    validator = BlueprintValidator()
    validated = validator.validate(blueprint.model_dump_json())
    assert validated.meta.app_type == BlueprintAppType.DASHBOARD


def test_compile_invoice():
    spec = AppSpec(
        app_type=AppType.INVOICE,
        title="Invoice App",
        description="Generate invoices",
        design=DesignPreferences(palette="corporate", font="classic", style_preset="professional", emoji_enabled=True),
        sections=[
            SectionSpec(
                section_id="client_info",
                title="Client Info",
                section_type=SectionType.INPUT_FORM,
                fields=[
                    FieldSpec(name="Name", field_type=FieldType.TEXT, default_value="Acme Corp"),
                ],
            ),
            SectionSpec(
                section_id="items",
                title="Line Items",
                section_type=SectionType.DATA_TABLE,
                repeatable=True,
                repeat_count=2,
                fields=[
                    FieldSpec(name="Item Name", field_type=FieldType.TEXT),
                    FieldSpec(name="Qty", field_type=FieldType.NUMBER, default_value=1),
                    FieldSpec(name="Rate", field_type=FieldType.CURRENCY, default_value=0.0),
                    FieldSpec(name="Amount", field_type=FieldType.FORMULA, formula="=Qty * Rate"),
                ],
            ),
            SectionSpec(
                section_id="totals",
                title="Summary",
                section_type=SectionType.SUMMARY,
                fields=[
                    FieldSpec(name="Subtotal", field_type=FieldType.FORMULA, formula="SUM(items.Amount)"),
                ],
            )
        ],
    )
    blueprint = compile_app_spec(spec)
    assert isinstance(blueprint, Blueprint)
    assert blueprint.meta.app_type == BlueprintAppType.INVOICE
    
    # Validate the generated blueprint
    validator = BlueprintValidator()
    validated = validator.validate(blueprint.model_dump_json())
    assert validated.meta.app_type == BlueprintAppType.INVOICE


def test_compile_tracker_fallback():
    spec = AppSpec(
        app_type=AppType.TRACKER,
        title="Task Tracker",
        description="Track daily tasks",
        sections=[
            SectionSpec(
                section_id="tasks",
                title="My Tasks",
                section_type=SectionType.DATA_TABLE,
                fields=[
                    FieldSpec(name="Task Name", field_type=FieldType.TEXT),
                    FieldSpec(name="Status", field_type=FieldType.DROPDOWN, options=["Todo", "Done"]),
                ],
            )
        ],
    )
    blueprint = compile_app_spec(spec)
    assert isinstance(blueprint, Blueprint)
    # Tracker should compile to BlueprintAppType.OTHER
    assert blueprint.meta.app_type == BlueprintAppType.OTHER


def test_compile_formula_injection_prevention():
    spec = AppSpec(
        app_type=AppType.POS,
        title="POS App",
        description="A Point of Sale application",
        sections=[
            SectionSpec(
                section_id="details",
                title="Transaction Details",
                section_type=SectionType.INPUT_FORM,
                fields=[
                    FieldSpec(name="Product", field_type=FieldType.DROPDOWN, options=["Coffee"]),
                    FieldSpec(name="Link", field_type=FieldType.FORMULA, formula='=HYPERLINK("http://evil.com", "Click")'),
                ],
            )
        ],
    )
    with pytest.raises(FormulaInjectionError) as excinfo:
        compile_app_spec(spec)
    assert "dangerous function" in str(excinfo.value)
