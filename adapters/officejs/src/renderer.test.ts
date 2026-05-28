import { describe, it, expect, vi } from 'vitest';
import { ExcelRenderer } from './renderer';
import { Blueprint } from './blueprint';
import posBlueprintJson from '../../../tests/fixtures/pos_blueprint.json';

describe('ExcelRenderer', () => {
  it('should translate pos_blueprint to Excel API calls correctly', async () => {
    const blueprint = posBlueprintJson as unknown as Blueprint;

    // Create mocks for Excel objects
    const mockBorder = {
      color: '',
      style: '',
      weight: ''
    };

    const mockBorders = {
      getItem: vi.fn().mockReturnValue(mockBorder)
    };

    const mockRangeFormat = {
      fill: { color: '' },
      font: { color: '', size: 10, bold: false, italic: false },
      horizontalAlignment: '',
      verticalAlignment: '',
      borders: mockBorders,
      columnWidth: 0,
      rowHeight: 0
    };

    const mockDataValidation = {
      clear: vi.fn(),
      rule: null as any,
      errorAlert: null as any
    };

    const mockRanges: Record<string, any> = {};

    const mockSheet = {
      showGridlines: true,
      freezePanes: {
        freezeRows: vi.fn(),
        freezeColumns: vi.fn()
      },
      getRange: vi.fn().mockImplementation((rangeStr: string) => {
        if (!mockRanges[rangeStr]) {
          mockRanges[rangeStr] = {
            format: {
              ...mockRangeFormat,
              fill: { ...mockRangeFormat.fill },
              font: { ...mockRangeFormat.font },
              borders: {
                getItem: vi.fn().mockReturnValue({
                  color: '',
                  style: '',
                  weight: ''
                })
              }
            },
            merge: vi.fn(),
            formulas: [[]] as string[][],
            values: [[]] as any[][],
            numberFormat: [[]] as string[][],
            dataValidation: {
              ...mockDataValidation,
              clear: vi.fn()
            }
          };
        }
        return mockRanges[rangeStr];
      })
    };

    const mockContext = {
      workbook: {
        worksheets: {
          getActiveWorksheet: vi.fn().mockReturnValue(mockSheet)
        }
      }
    } as unknown as Excel.RequestContext;

    // Instantiate and execute render
    const renderer = new ExcelRenderer();
    await renderer.render(blueprint, mockContext);

    // 1. Gridlines check
    // hide_gridlines in POS is false, so showGridlines should be true
    expect(mockSheet.showGridlines).toBe(true);

    // 2. Col widths check
    // "col_widths": {"A": 15.0, "B": 20.0, ...}
    // "A:A" range format columnWidth should be 15.0 * 8.43 = 126.45
    const colARange = mockSheet.getRange('A:A');
    expect(colARange.format.columnWidth).toBeCloseTo(126.45, 1);

    // 3. Merges check
    // merges: "A1:E2" and "D5:E5"
    expect(mockSheet.getRange('A1:E2').merge).toHaveBeenCalled();
    expect(mockSheet.getRange('D5:E5').merge).toHaveBeenCalled();

    // 4. Cells values and styling
    // Cell A1 value: "POINT OF SALE CHECKOUT"
    const cellA1 = mockSheet.getRange('A1');
    expect(cellA1.values).toEqual([['POINT OF SALE CHECKOUT']]);
    expect(cellA1.format.fill.color).toBe('#1A237E');
    expect(cellA1.format.font.color).toBe('#FFFFFF');
    expect(cellA1.format.font.size).toBe(16);
    expect(cellA1.format.font.bold).toBe(true);
    expect(cellA1.format.horizontalAlignment).toBe('Center');

    // Cell B10 formula: "=B6*B7"
    const cellB10 = mockSheet.getRange('B10');
    expect(cellB10.formulas).toEqual([['=B6*B7']]);
    expect(cellB10.format.font.bold).toBe(true);
    expect(cellB10.numberFormat).toEqual([['$#,##0.00']]);

    // Check borders for B10 (top border thin, bottom border double)
    expect(cellB10.format.borders.getItem).toHaveBeenCalledWith('EdgeTop');
    expect(cellB10.format.borders.getItem).toHaveBeenCalledWith('EdgeBottom');

    // Cell B5 validations
    const cellB5 = mockSheet.getRange('B5');
    expect(cellB5.dataValidation.clear).toHaveBeenCalled();
    expect(cellB5.dataValidation.rule.list.source).toBe('Coffee,Tea,Muffin,Croissant');

    // Cell D5 event button (macro VND script mock as hyperlink in Excel)
    const cellD5 = mockSheet.getRange('D5');
    expect(cellD5.formulas).toEqual([['=HYPERLINK("#ACTION_submit_order"; "Submit Order")']]);
  });
});
