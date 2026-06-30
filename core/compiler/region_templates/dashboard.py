"""
core/compiler/region_templates/dashboard.py — Dashboard app layout template.

Produces a deterministic Blueprint for dashboard applications:
  Row 1-2:  Title header (merged)
  Row 3:    Spacer
  Row 4:    KPI cards row (label|value pairs across columns)
  Row 5:    Spacer
  Row 6+:   Data table sections (header + data rows)
  ...       Spacer
  ...       Summary section
"""

from __future__ import annotations

from core.app_spec import AppSpec, FieldType, SectionType
from core.blueprint import AppType as BlueprintAppType
from core.blueprint import (
    Blueprint,
    Cell,
    Event,
    HAlign,
    MergeConfig,
    Meta,
    NamedRange,
    Region,
    VAlign,
)
from core.compiler.design_tokens import ResolvedTokens, resolve_format_hint
from core.compiler.region_templates.base import (
    FieldRegistry,
    build_validation,
    cell_range,
    cell_ref,
    field_type_to_format_hint,
    make_style,
    section_type_to_region_type,
)

# Dashboard uses wider columns to accommodate metrics
TOTAL_COLS = 6


def compile(spec: AppSpec, tokens: ResolvedTokens) -> Blueprint:
    """Compile a Dashboard AppSpec into a complete Blueprint.

    Args:
        spec: The semantic app specification.
        tokens: Resolved design tokens.

    Returns:
        A fully resolved Blueprint.
    """
    cells: list[Cell] = []
    regions: list[Region] = []
    merges: list[MergeConfig] = []
    named_ranges: list[NamedRange] = []
    registry = FieldRegistry()
    row_heights: dict[int, float] = {}
    cursor_row = 1

    # ── Title Header ──────────────────────────────────────────────
    title_text = spec.title
    if tokens.emoji_enabled and tokens.app_type_emoji:
        title_text = f"{tokens.app_type_emoji} {title_text}"

    header_start = cursor_row
    header_end = cursor_row + 1

    cells.append(Cell(
        cell_id=cell_ref(header_start, 1),
        value=title_text,
        style=make_style(
            tokens,
            bg_color=tokens.palette.primary,
            fg_color=tokens.palette.primary_text,
            bold=True,
            font_size=tokens.font.title_size,
            h_align=HAlign.CENTER,
            v_align=VAlign.MIDDLE,
        ),
    ))
    merges.append(MergeConfig(
        range=cell_range(header_start, 1, header_end, TOTAL_COLS)
    ))
    regions.append(Region(
        region_id="title_header",
        type=section_type_to_region_type("header"),
        anchor=cell_ref(header_start, 1),
        size=(2, TOTAL_COLS),
        title=spec.title,
        cell_ids=[cell_ref(header_start, 1)],
    ))
    row_heights[header_start] = tokens.style.row_height_title
    row_heights[header_end] = tokens.style.row_height_title
    cursor_row = header_end + 2  # spacer

    # ── KPI Row (from spec.kpis) ──────────────────────────────────
    if spec.kpis:
        kpi_start = cursor_row
        kpi_cell_ids: list[str] = []
        col = 1
        for kpi in spec.kpis:
            label_ref = cell_ref(cursor_row, col)
            value_ref = cell_ref(cursor_row, col + 1)
            kpi_cell_ids.extend([label_ref, value_ref])

            cells.append(Cell(
                cell_id=label_ref,
                value=kpi.label,
                style=make_style(
                    tokens,
                    bg_color=tokens.palette.secondary,
                    fg_color=tokens.palette.secondary_text,
                    bold=True,
                    h_align=HAlign.RIGHT,
                    border=tokens.style.header_border,
                ),
            ))

            fmt = resolve_format_hint(kpi.format_hint)
            # KPI formulas get resolved after all sections are placed
            # For now, store the semantic formula as a placeholder
            cells.append(Cell(
                cell_id=value_ref,
                value=f"[{kpi.formula}]",
                style=make_style(
                    tokens,
                    bold=True,
                    font_size=tokens.font.header_size,
                    number_format=fmt,
                    h_align=HAlign.CENTER,
                    border=tokens.style.header_border,
                ),
            ))
            col += 2

        regions.append(Region(
            region_id="kpi_row",
            type=section_type_to_region_type("kpi_row"),
            anchor=cell_ref(kpi_start, 1),
            size=(1, min(col - 1, TOTAL_COLS)),
            title="Key Metrics",
            cell_ids=kpi_cell_ids,
        ))
        row_heights[cursor_row] = tokens.style.row_height_header
        cursor_row += 2  # spacer

    # ── Process sections ──────────────────────────────────────────
    for section in spec.sections:
        if section.section_type == SectionType.HEADER:
            # Already rendered as title header
            for fld in section.fields:
                registry.register(
                    section.section_id, fld.name, cell_ref(1, 1)
                )
            continue

        section_start = cursor_row
        section_cell_ids: list[str] = []

        # Section title row
        emoji = tokens.section_emojis.get(section.section_type.value, "")
        section_title = (
            f"{emoji} {section.title}" if emoji else section.title
        )
        cells.append(Cell(
            cell_id=cell_ref(cursor_row, 1),
            value=section_title,
            style=make_style(
                tokens,
                bg_color=tokens.palette.secondary,
                fg_color=tokens.palette.secondary_text,
                bold=True,
                font_size=tokens.font.header_size,
                border=tokens.style.header_border,
            ),
        ))
        merges.append(MergeConfig(
            range=cell_range(cursor_row, 1, cursor_row, TOTAL_COLS)
        ))
        section_cell_ids.append(cell_ref(cursor_row, 1))
        row_heights[cursor_row] = tokens.style.row_height_header
        cursor_row += 1

        if section.section_type == SectionType.KPI_ROW:
            # KPI cards inline in sections
            col = 1
            for fld in section.fields:
                label_ref = cell_ref(cursor_row, col)
                value_ref = cell_ref(cursor_row, col + 1)
                section_cell_ids.extend([label_ref, value_ref])

                cells.append(Cell(
                    cell_id=label_ref,
                    value=fld.name,
                    style=make_style(
                        tokens,
                        bg_color=tokens.palette.label_bg,
                        bold=True,
                        h_align=HAlign.RIGHT,
                        border=tokens.style.cell_border,
                    ),
                ))

                fmt = resolve_format_hint(
                    fld.format_hint
                    or field_type_to_format_hint(fld.field_type)
                )
                if fld.field_type == FieldType.FORMULA and fld.formula:
                    resolved = registry.resolve_formula(
                        fld.formula,
                        current_row=cursor_row,
                        section_id=section.section_id,
                    )
                    cells.append(Cell(
                        cell_id=value_ref,
                        formula=resolved,
                        style=make_style(
                            tokens,
                            bold=True,
                            number_format=fmt,
                            border=tokens.style.cell_border,
                        ),
                    ))
                else:
                    cells.append(Cell(
                        cell_id=value_ref,
                        value=fld.default_value,
                        style=make_style(
                            tokens,
                            number_format=fmt,
                            border=tokens.style.cell_border,
                        ),
                    ))

                registry.register(
                    section.section_id, fld.name, value_ref
                )
                col += 2
            row_heights[cursor_row] = tokens.style.row_height_header
            cursor_row += 1

        elif section.section_type == SectionType.DATA_TABLE:
            # Column headers
            for ci, fld in enumerate(section.fields, start=1):
                hdr_ref = cell_ref(cursor_row, ci)
                section_cell_ids.append(hdr_ref)
                cells.append(Cell(
                    cell_id=hdr_ref,
                    value=fld.name,
                    style=make_style(
                        tokens,
                        bg_color=tokens.palette.primary,
                        fg_color=tokens.palette.primary_text,
                        bold=True,
                        h_align=HAlign.CENTER,
                        border=tokens.style.header_border,
                    ),
                ))
            row_heights[cursor_row] = tokens.style.row_height_header
            cursor_row += 1

            # Data rows
            repeat = section.repeat_count if section.repeatable else 1
            for row_idx in range(repeat):
                for ci, fld in enumerate(section.fields, start=1):
                    data_ref = cell_ref(cursor_row, ci)
                    section_cell_ids.append(data_ref)

                    fmt = resolve_format_hint(
                        fld.format_hint
                        or field_type_to_format_hint(fld.field_type)
                    )
                    validation = build_validation(fld)

                    if fld.field_type == FieldType.FORMULA and fld.formula:
                        resolved = registry.resolve_formula(
                            fld.formula,
                            current_row=cursor_row,
                            section_id=section.section_id,
                        )
                        cells.append(Cell(
                            cell_id=data_ref,
                            formula=resolved,
                            style=make_style(
                                tokens,
                                number_format=fmt,
                                border=tokens.style.cell_border,
                            ),
                        ))
                    else:
                        cells.append(Cell(
                            cell_id=data_ref,
                            value=fld.default_value,
                            style=make_style(
                                tokens,
                                bg_color=tokens.palette.input_bg,
                                number_format=fmt,
                                border=tokens.style.cell_border,
                            ),
                            validation=validation,
                        ))

                    registry.register(
                        section.section_id, fld.name, data_ref
                    )
                row_heights[cursor_row] = tokens.style.row_height_base
                cursor_row += 1

        elif section.section_type in (
            SectionType.INPUT_FORM, SectionType.SUMMARY
        ):
            for fld in section.fields:
                label_ref = cell_ref(cursor_row, 1)
                value_ref = cell_ref(cursor_row, 2)
                section_cell_ids.extend([label_ref, value_ref])

                cells.append(Cell(
                    cell_id=label_ref,
                    value=fld.name,
                    style=make_style(
                        tokens,
                        bg_color=(
                            tokens.palette.label_bg
                            if tokens.style.use_section_fills
                            else None
                        ),
                        bold=True,
                        border=tokens.style.cell_border,
                    ),
                ))

                fmt = resolve_format_hint(
                    fld.format_hint
                    or field_type_to_format_hint(fld.field_type)
                )
                validation = build_validation(fld)

                if fld.field_type == FieldType.FORMULA and fld.formula:
                    resolved = registry.resolve_formula(
                        fld.formula,
                        current_row=cursor_row,
                        section_id=section.section_id,
                    )
                    cells.append(Cell(
                        cell_id=value_ref,
                        formula=resolved,
                        style=make_style(
                            tokens,
                            bold=True,
                            number_format=fmt,
                            border=tokens.style.cell_border,
                        ),
                    ))
                else:
                    cells.append(Cell(
                        cell_id=value_ref,
                        value=fld.default_value,
                        style=make_style(
                            tokens,
                            bg_color=tokens.palette.input_bg,
                            number_format=fmt,
                            border=tokens.style.cell_border,
                        ),
                        validation=validation,
                    ))

                registry.register(
                    section.section_id, fld.name, value_ref
                )
                row_heights[cursor_row] = tokens.style.row_height_base
                cursor_row += 1

        elif section.section_type == SectionType.ACTIONS:
            for ai, fld in enumerate(section.fields):
                btn_ref = cell_ref(cursor_row, ai + 1)
                section_cell_ids.append(btn_ref)
                cells.append(Cell(
                    cell_id=btn_ref,
                    value=fld.name,
                    style=make_style(
                        tokens,
                        bg_color=tokens.palette.success,
                        fg_color=tokens.palette.primary_text,
                        bold=True,
                        h_align=HAlign.CENTER,
                        border=tokens.style.cell_border,
                    ),
                    event=Event(
                        type="button",
                        action=fld.name.lower().replace(" ", "_"),
                    ),
                ))
                registry.register(
                    section.section_id, fld.name, btn_ref
                )
            row_heights[cursor_row] = tokens.style.row_height_header
            cursor_row += 1

        # Build Region
        section_rows = cursor_row - section_start
        num_cols = max(2, len(section.fields))
        regions.append(Region(
            region_id=section.section_id,
            type=section_type_to_region_type(section.section_type.value),
            anchor=cell_ref(section_start, 1),
            size=(section_rows, min(num_cols, TOTAL_COLS)),
            title=section.title,
            cell_ids=section_cell_ids,
        ))
        cursor_row += 1  # spacer

    # ── Resolve KPI formulas now that all fields are registered ───
    _resolve_kpi_formulas(cells, spec, registry)

    # ── Build Meta ────────────────────────────────────────────────
    col_widths: dict[str, float] = {}
    for c in range(1, TOTAL_COLS + 1):
        letter = cell_ref(1, c)[0]
        col_widths[letter] = tokens.style.col_width_data

    meta = Meta(
        app_type=BlueprintAppType.DASHBOARD,
        title=spec.title,
        description=spec.description,
        frozen_rows=2,
        frozen_cols=0,
        hide_gridlines=True,
        col_widths=col_widths,
        row_heights=row_heights,
    )

    return Blueprint(
        meta=meta,
        regions=regions,
        cells=cells,
        merges=merges,
        named_ranges=named_ranges,
    )


def _resolve_kpi_formulas(
    cells: list[Cell],
    spec: AppSpec,
    registry: FieldRegistry,
) -> None:
    """Resolve KPI placeholder formulas to real cell references.

    Mutates Cell objects in-place to replace placeholder values
    with resolved formulas.

    Args:
        cells: List of all cells in the blueprint.
        spec: The app specification containing KPI definitions.
        registry: Populated field registry.
    """
    for kpi in spec.kpis:
        placeholder = f"[{kpi.formula}]"
        for cell in cells:
            if cell.value == placeholder:
                resolved = registry.resolve_formula(kpi.formula)
                # If resolution changed the formula (has cell refs),
                # use it. Otherwise keep as a display value.
                if resolved.startswith("=") or resolved != kpi.formula:
                    cell.formula = resolved
                    cell.value = None
                break
