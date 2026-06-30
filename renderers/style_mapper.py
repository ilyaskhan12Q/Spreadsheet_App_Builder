"""
renderers/style_mapper.py
Converts Blueprint style definitions to openpyxl styles.
"""
from typing import Any

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from core.blueprint import CellStyle


def hex_to_argb(hex_color: str) -> str:
    """Convert #RRGGBB to AARRGGBB for openpyxl."""
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    if len(hex_color) == 6:
        return f"FF{hex_color.upper()}"
    return hex_color.upper()

def get_openpyxl_styles(style: CellStyle | None) -> dict[str, Any]:
    """Returns a dict of openpyxl style objects from a CellStyle."""
    styles: dict[str, Any] = {}
    if not style:
        return styles

    # Font
    font_kwargs: dict[str, Any] = {}
    if style.font_size:
        font_kwargs['size'] = style.font_size
    if style.bold:
        font_kwargs['bold'] = True
    if style.italic:
        font_kwargs['italic'] = True
    if style.fg_color:
        font_kwargs['color'] = hex_to_argb(style.fg_color)
    if font_kwargs:
        styles['font'] = Font(**font_kwargs)

    # Alignment
    align_kwargs: dict[str, Any] = {}
    if style.h_align:
        align_kwargs['horizontal'] = style.h_align.value
    if style.v_align:
        v_val = style.v_align.value
        align_kwargs['vertical'] = 'center' if v_val == 'middle' else v_val
    if align_kwargs:
        styles['alignment'] = Alignment(**align_kwargs)

    # Fill
    if style.bg_color:
        argb = hex_to_argb(style.bg_color)
        styles['fill'] = PatternFill(start_color=argb, end_color=argb, fill_type="solid")

    # Borders
    border_kwargs: dict[str, Any] = {}
    for edge in ['top', 'bottom', 'left', 'right']:
        val = getattr(style, f'border_{edge}')
        if val and val.value != "none":
            b_style = 'thick' if val.value == 'thick' else 'thin'
            border_kwargs[edge] = Side(border_style=b_style, color='FF000000')
    if border_kwargs:
        styles['border'] = Border(**border_kwargs)

    return styles
