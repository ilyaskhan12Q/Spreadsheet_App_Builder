from typing import Any, Dict, Optional
from core.blueprint import CellStyle, BorderStyle, HAlign, VAlign

try:
    import uno  # type: ignore
    from com.sun.star.awt import FontWeight, FontSlant  # type: ignore
    from com.sun.star.table import CellHJustify, CellVJustify  # type: ignore
    from com.sun.star.table import BorderLine2  # type: ignore
    UNO_AVAILABLE = True
except ImportError:
    # Fallback to constants for unit tests without UNO environment
    class FontWeight:  # type: ignore[no-redef]
        NORMAL = 100.0
        BOLD = 150.0

    class FontSlant:  # type: ignore[no-redef]
        NONE = 0
        ITALIC = 1

    class CellHJustify:  # type: ignore[no-redef]
        STANDARD = 0
        LEFT = 1
        CENTER = 2
        RIGHT = 3
        BLOCK = 4

    class CellVJustify:  # type: ignore[no-redef]
        STANDARD = 0
        TOP = 1
        CENTER = 2
        BOTTOM = 3

    class BorderLine2:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.Color = 0
            self.InnerLineWidth = 0
            self.OuterLineWidth = 0
            self.LineDistance = 0
            self.LineStyle = 0

    UNO_AVAILABLE = False


def hex_to_uno_color(hex_str: Optional[str]) -> Optional[int]:
    """Convert hex string (e.g. '#FF0000' or '#FFF') to UNO color integer."""
    if not hex_str:
        return None
    hex_clean = hex_str.lstrip('#')
    if len(hex_clean) == 3:
        hex_clean = "".join([c*2 for c in hex_clean])
    try:
        return int(hex_clean, 16)
    except ValueError:
        return None


def get_border_line(border_style: BorderStyle, color_int: int = 0) -> Any:
    """Returns a UNO BorderLine2 object or a mock representation."""
    if border_style == BorderStyle.NONE:
        return None

    if UNO_AVAILABLE:
        # Create a real UNO struct if possible
        try:
            # Note: com.sun.star.table.BorderLine2 is a struct, create via uno.createUnoStruct
            line = uno.createUnoStruct("com.sun.star.table.BorderLine2")
        except Exception:
            line = BorderLine2()
    else:
        line = BorderLine2()

    line.Color = color_int
    
    if border_style == BorderStyle.THIN:
        line.OuterLineWidth = 10
    elif border_style == BorderStyle.MEDIUM:
        line.OuterLineWidth = 30
    elif border_style == BorderStyle.THICK:
        line.OuterLineWidth = 50
    elif border_style == BorderStyle.DOUBLE:
        line.OuterLineWidth = 10
        line.InnerLineWidth = 10
        line.LineDistance = 10
    elif border_style == BorderStyle.DASHED:
        line.OuterLineWidth = 20
        # LineStyle 2 represents dashed in com.sun.star.table.BorderLineStyle
        line.LineStyle = 2
    elif border_style == BorderStyle.DOTTED:
        line.OuterLineWidth = 10
        # LineStyle 3 represents dotted in com.sun.star.table.BorderLineStyle
        line.LineStyle = 3
    
    return line


def map_cell_style(style: CellStyle) -> Dict[str, Any]:
    """
    Maps a blueprint CellStyle to a dictionary of UNO properties/attributes.
    """
    uno_props: Dict[str, Any] = {}

    # Background and Text Color
    if style.bg_color:
        uno_props["CellBackColor"] = hex_to_uno_color(style.bg_color)
    if style.fg_color:
        uno_props["CharColor"] = hex_to_uno_color(style.fg_color)

    # Font properties
    uno_props["CharHeight"] = style.font_size
    uno_props["CharWeight"] = FontWeight.BOLD if style.bold else FontWeight.NORMAL
    uno_props["CharPosture"] = FontSlant.ITALIC if style.italic else FontSlant.NONE

    # Horizontal Alignment
    if style.h_align == HAlign.LEFT:
        uno_props["HJustify"] = CellHJustify.LEFT
    elif style.h_align == HAlign.CENTER:
        uno_props["HJustify"] = CellHJustify.CENTER
    elif style.h_align == HAlign.RIGHT:
        uno_props["HJustify"] = CellHJustify.RIGHT
    elif style.h_align == HAlign.JUSTIFY:
        uno_props["HJustify"] = CellHJustify.BLOCK

    # Vertical Alignment
    if style.v_align == VAlign.TOP:
        uno_props["VJustify"] = CellVJustify.TOP
    elif style.v_align == VAlign.MIDDLE:
        uno_props["VJustify"] = CellVJustify.CENTER
    elif style.v_align == VAlign.BOTTOM:
        uno_props["VJustify"] = CellVJustify.BOTTOM

    # Border properties (each side)
    # Note: LibreOffice cells support TopBorder, BottomBorder, LeftBorder, RightBorder properties
    text_color_int = hex_to_uno_color(style.fg_color) or 0
    
    if style.border_top != BorderStyle.NONE:
        uno_props["TopBorder"] = get_border_line(style.border_top, text_color_int)
    if style.border_bottom != BorderStyle.NONE:
        uno_props["BottomBorder"] = get_border_line(style.border_bottom, text_color_int)
    if style.border_left != BorderStyle.NONE:
        uno_props["LeftBorder"] = get_border_line(style.border_left, text_color_int)
    if style.border_right != BorderStyle.NONE:
        uno_props["RightBorder"] = get_border_line(style.border_right, text_color_int)

    return uno_props
