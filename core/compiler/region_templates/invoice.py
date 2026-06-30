"""
core/compiler/region_templates/invoice.py — Invoice app layout template.

Produces a deterministic Blueprint for invoice applications:
  Row 1-3:  Company header (merged)
  Row 4:    Spacer
  Row 5+:   Client info (input form)
  ...       Spacer
  ...       Line items table (repeatable)
  ...       Spacer
  ...       Summary (subtotal, tax, total)
  ...       Spacer
  ...       Action buttons
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

# Invoice uses 6 columns for line items (Description, Qty, Rate, Amount, etc.)
TOTAL_COLS = 6


def compile(spec: AppSpec, tokens: ResolvedTokens) -> Blueprint:
    """Compile an Invoice AppSpec into a complete Blueprint.

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

    # ── Company Header (3 rows) ───────────────────────────────────
    title_text = spec.title
    if tokens.emoji_enabled and tokens.app_type_emoji:
        title_text = f"{tokens.app_type_emoji} {title_text}"

    header_start = cursor_row
    header_end = cursor_row + 2  # 3 rows for a more prominent header

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
        size=(3, TOTAL_COLS),
        title=spec.title,
        cell_ids=[cell_ref(header_start, 1)],
    ))
    for r in range(header_start, header_end + 1):
        row_heights[r] = tokens.style.row_height_title
    cursor_row = header_end + 2  # spacer

    # ── Process sections ──────────────────────────────────────────
    for section in spec.sections:
        if section.section_type == SectionType.HEADER:
            # Register header fields but don't re-render
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

        if section.section_type in (
            SectionType.INPUT_FORM, SectionType.SUMMARY
        ):
            # Label | Value pairs
            for fld in section.fields:
                label_ref = cell_ref(cursor_row, 1)
                value_ref = cell_ref(cursor_row, 2)
                section_cell_ids.extend([label_ref, value_ref])

                # For summary, merge the value across remaining cols
                is_summary = section.section_type == SectionType.SUMMARY
                if is_summary:
                    # Label in right half, value at far right
                    label_ref = cell_ref(cursor_row, TOTAL_COLS - 1)
                    value_ref = cell_ref(cursor_row, TOTAL_COLS)
                    section_cell_ids = section_cell_ids[:-2]
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
                        h_align=HAlign.RIGHT if is_summary else HAlign.LEFT,
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
                            bg_color=tokens.palette.input_bg,
                            bold=is_summary,
                            number_format=fmt,
                            border=tokens.style.cell_border,
                            h_align=HAlign.RIGHT if is_summary else HAlign.LEFT,
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

        elif section.section_type == SectionType.ACTIONS:
            for ai, fld in enumerate(section.fields):
                btn_ref = cell_ref(cursor_row, ai + 1)
                section_cell_ids.append(btn_ref)

                action_id = fld.name.lower().replace(" ", "_")
                style_color = tokens.palette.success
                for act in spec.actions:
                    if act.action_id == action_id:
                        if act.style_hint == "danger":
                            style_color = tokens.palette.danger
                        elif act.style_hint == "secondary":
                            style_color = tokens.palette.secondary
                        break

                cells.append(Cell(
                    cell_id=btn_ref,
                    value=fld.name,
                    style=make_style(
                        tokens,
                        bg_color=style_color,
                        fg_color=tokens.palette.primary_text,
                        bold=True,
                        h_align=HAlign.CENTER,
                        v_align=VAlign.MIDDLE,
                        border=tokens.style.cell_border,
                    ),
                    event=Event(type="button", action=action_id),
                ))
                registry.register(
                    section.section_id, fld.name, btn_ref
                )
            row_heights[cursor_row] = tokens.style.row_height_header
            cursor_row += 1

        elif section.section_type == SectionType.KPI_ROW:
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

        # Build Region
        section_rows = cursor_row - section_start
        if section.section_type == SectionType.SUMMARY:
            num_cols = TOTAL_COLS
        elif section.section_type == SectionType.KPI_ROW:
            num_cols = 2 * len(section.fields)
        else:
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

    # ── Build Meta ────────────────────────────────────────────────
    col_widths: dict[str, float] = {}
    for c in range(1, TOTAL_COLS + 1):
        letter = cell_ref(1, c)[0]
        if c == 1:
            col_widths[letter] = tokens.style.col_width_label + 4
        else:
            col_widths[letter] = tokens.style.col_width_data
    # Description column wider
    col_widths["A"] = tokens.style.col_width_label + 4

    meta = Meta(
        app_type=BlueprintAppType.INVOICE,
        title=spec.title,
        description=spec.description,
        frozen_rows=3,
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
