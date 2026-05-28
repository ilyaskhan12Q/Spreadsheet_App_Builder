from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class AppType(str, Enum):
    POS = "pos"
    DASHBOARD = "dashboard"
    INVOICE = "invoice"
    OTHER = "other"


class RegionType(str, Enum):
    HEADER = "header"
    INPUT = "input"
    OUTPUT = "output"
    DATA_TABLE = "data_table"
    CHART_PLACEHOLDER = "chart_placeholder"
    KPI_CARD = "kpi_card"


class BorderStyle(str, Enum):
    NONE = "none"
    THIN = "thin"
    MEDIUM = "medium"
    THICK = "thick"
    DOUBLE = "double"
    DASHED = "dashed"
    DOTTED = "dotted"


class HAlign(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class VAlign(str, Enum):
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


class CellStyle(BaseModel):
    bg_color: Optional[str] = Field(
        None,
        description="Background color as hex string, e.g., '#FFFFFF' or '#3F51B5'."
    )
    fg_color: Optional[str] = Field(
        None,
        description="Foreground text color as hex string, e.g., '#000000' or '#E0E0E0'."
    )
    font_size: float = Field(
        10.0,
        description="Font size in points, e.g., 10.0, 12.0, 14.0."
    )
    bold: bool = Field(
        False,
        description="True if text should be bold, otherwise False."
    )
    italic: bool = Field(
        False,
        description="True if text should be italic, otherwise False."
    )
    border_top: BorderStyle = Field(
        BorderStyle.NONE,
        description="Border style for the top side."
    )
    border_bottom: BorderStyle = Field(
        BorderStyle.NONE,
        description="Border style for the bottom side."
    )
    border_left: BorderStyle = Field(
        BorderStyle.NONE,
        description="Border style for the left side."
    )
    border_right: BorderStyle = Field(
        BorderStyle.NONE,
        description="Border style for the right side."
    )
    number_format: Optional[str] = Field(
        None,
        description="Excel/LibreOffice number format pattern, e.g., '0.00', '$#,##0.00', 'yyyy-mm-dd'."
    )
    h_align: HAlign = Field(
        HAlign.LEFT,
        description="Horizontal alignment of the cell text."
    )
    v_align: VAlign = Field(
        VAlign.MIDDLE,
        description="Vertical alignment of the cell text."
    )


class Validation(BaseModel):
    type: str = Field(
        ...,
        description="Type of validation, e.g., 'list', 'decimal', 'whole', 'date', 'text_length'."
    )
    formula1: str = Field(
        ...,
        description="Validation criteria, source list, or expression, e.g., 'Cash,Card,Online' or '=Sheet2!$A$1:$A$10'."
    )
    allow_blank: bool = Field(
        True,
        description="True if blank cell is allowed during validation."
    )
    error_message: Optional[str] = Field(
        None,
        description="Custom error message to display when validation fails."
    )


class Event(BaseModel):
    type: str = Field(
        "button",
        description="Type of event trigger. Currently 'button' is supported."
    )
    action: str = Field(
        ...,
        description="Name of the macro trigger action/function, e.g., 'submit_order'."
    )


class Cell(BaseModel):
    cell_id: str = Field(
        ...,
        description="Cell reference in A1 notation, e.g., 'A1', 'C15'."
    )
    value: Any = Field(
        None,
        description="Direct cell value, which can be a string, number, or boolean."
    )
    formula: Optional[str] = Field(
        None,
        description="Formula string starting with '='. E.g., '=SUM(B2:B10)'."
    )
    style: Optional[CellStyle] = Field(
        None,
        description="Cell styling attributes."
    )
    validation: Optional[Validation] = Field(
        None,
        description="Cell data validation rules."
    )
    event: Optional[Event] = Field(
        None,
        description="Interactive event configuration for the cell (such as click macros for buttons)."
    )


class MergeConfig(BaseModel):
    range: str = Field(
        ...,
        description="Cell range to merge in A1 notation, e.g., 'A1:C2'."
    )


class NamedRange(BaseModel):
    name: str = Field(
        ...,
        description="Unique identifier name for the range, e.g., 'ProductsList'."
    )
    range: str = Field(
        ...,
        description="Range in A1 notation (can include sheet name), e.g., 'Sheet1!B5:B10'."
    )


class Region(BaseModel):
    region_id: str = Field(
        ...,
        description="Unique identifier for the region within the sheet."
    )
    type: RegionType = Field(
        ...,
        description="Logical region type."
    )
    anchor: str = Field(
        ...,
        description="Top-left starting cell of the region in A1 notation, e.g., 'A1'."
    )
    size: Tuple[int, int] = Field(
        ...,
        description="Size of the region as (rows, cols) dimensions, e.g., (10, 5)."
    )
    title: Optional[str] = Field(
        None,
        description="Header/Title text for the region."
    )
    cell_ids: List[str] = Field(
        ...,
        description="List of cell references belonging to this region in A1 notation."
    )


class Meta(BaseModel):
    app_type: AppType = Field(
        ...,
        description="High level category of spreadsheet application."
    )
    title: str = Field(
        ...,
        description="Title of the spreadsheet application."
    )
    description: str = Field(
        ...,
        description="Brief summary explaining what the app does."
    )
    author: str = Field(
        "SAB Engine",
        description="Author or creator identity."
    )
    version: str = Field(
        "1.0.0",
        description="Version string."
    )
    frozen_rows: int = Field(
        0,
        description="Number of rows to freeze starting from the top."
    )
    frozen_cols: int = Field(
        0,
        description="Number of columns to freeze starting from the left."
    )
    hide_gridlines: bool = Field(
        False,
        description="True to hide default gridlines, False to show them."
    )
    col_widths: Dict[str, float] = Field(
        default_factory=dict,
        description="Custom width values for columns (col letter -> width in points/chars)."
    )
    row_heights: Dict[int, float] = Field(
        default_factory=dict,
        description="Custom height values for rows (row number -> height in points/chars)."
    )


class Blueprint(BaseModel):
    meta: Meta = Field(
        ...,
        description="Metadata and display settings for the spreadsheet."
    )
    regions: List[Region] = Field(
        ...,
        description="List of functional regions grouping cells together."
    )
    cells: List[Cell] = Field(
        ...,
        description="Individual cell definitions including content and styles."
    )
    merges: List[MergeConfig] = Field(
        default_factory=list,
        description="Ranges that should be merged."
    )
    named_ranges: List[NamedRange] = Field(
        default_factory=list,
        description="Definitions of named ranges."
    )
