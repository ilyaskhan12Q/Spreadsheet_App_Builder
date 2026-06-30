import re

from core.blueprint import Blueprint


class LayoutConflictError(ValueError):
    """Exception raised for layout conflicts or constraint violations in the blueprint."""
    pass


def parse_cell_id(cell_id: str) -> tuple[int, int]:
    """Parse cell reference (e.g., 'A1', 'Sheet1!B5') into (row, col) index (1-based)."""
    # Strip sheet prefix if present
    if "!" in cell_id:
        cell_id = cell_id.split("!")[-1]

    match = re.match(r"^([A-Z]+)([0-9]+)$", cell_id.upper())
    if not match:
        raise LayoutConflictError(f"Invalid cell reference format: '{cell_id}'")

    col_str, row_str = match.groups()
    row = int(row_str)

    col = 0
    for char in col_str:
        col = col * 26 + (ord(char) - ord('A') + 1)

    return row, col


def parse_range(range_str: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """Parse range (e.g., 'A1:C3') into ((start_row, start_col), (end_row, end_col))."""
    if "!" in range_str:
        range_str = range_str.split("!")[-1]

    if ":" not in range_str:
        r, c = parse_cell_id(range_str)
        return (r, c), (r, c)

    parts = range_str.split(":")
    if len(parts) != 2:
        raise LayoutConflictError(f"Invalid range format: '{range_str}'")

    start_cell, end_cell = parts
    return parse_cell_id(start_cell), parse_cell_id(end_cell)


def check_bounds(blueprint: Blueprint, max_row: int = 1000, max_col: int = 50) -> None:
    """Check that all cell references in cells, regions, merges, and named ranges are within bounds."""
    # Check individual cells
    for cell in blueprint.cells:
        r, c = parse_cell_id(cell.cell_id)
        if r <= 0 or c <= 0 or r > max_row or c > max_col:
            raise LayoutConflictError(
                f"Cell {cell.cell_id} is out of bounds. Row must be in 1..{max_row}, Col must be in 1..{max_col}."
            )

    # Check regions
    for region in blueprint.regions:
        r, c = parse_cell_id(region.anchor)
        rows, cols = region.size
        end_row = r + rows - 1
        end_col = c + cols - 1

        if r <= 0 or c <= 0 or end_row > max_row or end_col > max_col:
            raise LayoutConflictError(
                f"Region {region.region_id} (anchor: {region.anchor}, size: {region.size}) exceeds boundaries. "
                f"Bottom-right cell ({end_row}, {end_col}) must be in bounds."
            )

        for cell_id in region.cell_ids:
            cr, cc = parse_cell_id(cell_id)
            if cr < r or cr > end_row or cc < c or cc > end_col:
                raise LayoutConflictError(
                    f"Cell {cell_id} belongs to region {region.region_id} but is outside its anchor boundaries "
                    f"[{r}..{end_row}, {c}..{end_col}]."
                )

    # Check merges
    for m in blueprint.merges:
        (sr, sc), (er, ec) = parse_range(m.range)
        if sr <= 0 or sc <= 0 or er > max_row or ec > max_col:
            raise LayoutConflictError(
                f"Merge range '{m.range}' is out of bounds. Boundaries must be within (1..{max_row}, 1..{max_col})."
            )

    # Check named ranges
    for nr in blueprint.named_ranges:
        (sr, sc), (er, ec) = parse_range(nr.range)
        if sr <= 0 or sc <= 0 or er > max_row or ec > max_col:
            raise LayoutConflictError(
                f"Named range '{nr.name}' ({nr.range}) is out of bounds."
            )


def check_merge_conflicts(blueprint: Blueprint) -> None:
    """Ensure no cells overlap in multiple merge ranges."""
    merged_cells = set()
    for m in blueprint.merges:
        (sr, sc), (er, ec) = parse_range(m.range)
        for r in range(sr, er + 1):
            for c in range(sc, ec + 1):
                cell_coord = (r, c)
                if cell_coord in merged_cells:
                    raise LayoutConflictError(
                        f"Overlap detected at row {r}, col {c} in multiple merge configurations (violating range '{m.range}')."
                    )
                merged_cells.add(cell_coord)


def check_formula_syntax(blueprint: Blueprint) -> None:
    """Validate that formulas start with '='."""
    for cell in blueprint.cells:
        if cell.formula is not None:
            formula_stripped = cell.formula.strip()
            if not formula_stripped.startswith("="):
                raise LayoutConflictError(
                    f"Formula for cell {cell.cell_id} must start with '='. Found: '{cell.formula}'"
                )
