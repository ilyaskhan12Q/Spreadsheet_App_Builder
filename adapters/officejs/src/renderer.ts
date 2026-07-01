import { Blueprint } from './blueprint';
import { applyCellStyle } from './styleMapper';

export class ExcelRenderer {
  public async render(blueprint: Blueprint, context: Excel.RequestContext): Promise<void> {
    const sheet = context.workbook.worksheets.getActiveWorksheet();

    // 1. Gridlines
    this.hideGridlines(sheet, blueprint.meta.hide_gridlines);

    // 2. Freeze Panes
    this.freezePanes(sheet, blueprint.meta.frozen_rows, blueprint.meta.frozen_cols);

    // 3. Render Regions (col widths, row heights, merges)
    this.renderRegions(sheet, blueprint);

    // 4. Render Cells (values, formulas, validations, styles)
    this.renderCells(sheet, blueprint);

    // 5. Render Events (wire up action button hyperlinks)
    this.renderEvents(sheet, blueprint);
  }

  private hideGridlines(sheet: Excel.Worksheet, hide: boolean): void {
    sheet.showGridlines = !hide;
  }

  private freezePanes(sheet: Excel.Worksheet, rows: number, cols: number): void {
    if (rows > 0 || cols > 0) {
      sheet.freezePanes.freezeRows(rows);
      sheet.freezePanes.freezeColumns(cols);
    }
  }

  private renderRegions(sheet: Excel.Worksheet, blueprint: Blueprint): void {
    // Column widths
    Object.entries(blueprint.meta.col_widths).forEach(([col, width]) => {
      const colRange = sheet.getRange(`${col}:${col}`);
      colRange.format.columnWidth = width * 8.43; // approximate points to char width conversion
    });

    // Row heights
    Object.entries(blueprint.meta.row_heights).forEach(([row, height]) => {
      const rowRange = sheet.getRange(`${row}:${row}`);
      rowRange.format.rowHeight = height;
    });

    // Perform merges
    blueprint.merges.forEach((m) => {
      const range = sheet.getRange(m.range);
      range.merge();
    });
  }

  private renderCells(sheet: Excel.Worksheet, blueprint: Blueprint): void {
    blueprint.cells.forEach((cell) => {
      const range = sheet.getRange(cell.cell_id);

      // Set value or formula
      if (cell.formula) {
        range.formulas = [[cell.formula]];
      } else if (cell.value !== undefined && cell.value !== null) {
        range.values = [[cell.value]];
      }

      // Apply cell styling
      if (cell.style) {
        applyCellStyle(range, cell.style);
      }

      // Apply data validation
      if (cell.validation) {
        const validation = range.dataValidation;
        validation.clear();

        if (cell.validation.type === 'list') {
          validation.rule = {
            list: {
              inCellDropDown: true,
              source: cell.validation.formula1
            }
          };
        } else if (cell.validation.type === 'whole' || cell.validation.type === 'decimal') {
          // Default to greater than or equal to for numeric boundary checks
          const op = cell.validation.formula1.includes('>=') ? 'GreaterThanOrEqualTo' : 'EqualTo';
          const valClean = cell.validation.formula1.replace('>=', '').trim();
          validation.rule = {
            wholeNumber: {
              formula1: valClean,
              operator: op as any
            }
          };
        }

        if (cell.validation.error_message) {
          validation.errorAlert = {
            message: cell.validation.error_message,
            showAlert: true,
            style: "Stop",
            title: "Data Validation Error"
          };
        }
      }
    });
  }

  private renderEvents(sheet: Excel.Worksheet, blueprint: Blueprint): void {
    blueprint.cells.forEach((cell) => {
      if (cell.event && cell.event.type === 'button') {
        const range = sheet.getRange(cell.cell_id);
        const label = cell.value || "Click Here";
        // Wire macro stub behavior via hyperlink triggering custom action string
        range.formulas = [[`=HYPERLINK("#ACTION_${cell.event.action}"; "${label}")`]];
      }
    });
  }
}
