import { CellStyle } from './blueprint';

export function applyCellStyle(range: Excel.Range, style: CellStyle): void {
  if (style.bg_color) {
    range.format.fill.color = style.bg_color;
  }
  if (style.fg_color) {
    range.format.font.color = style.fg_color;
  }
  if (style.font_size) {
    range.format.font.size = style.font_size;
  }
  if (style.bold !== undefined) {
    range.format.font.bold = style.bold;
  }
  if (style.italic !== undefined) {
    range.format.font.italic = style.italic;
  }

  // Alignment mapping
  if (style.h_align) {
    switch (style.h_align) {
      case 'left':
        range.format.horizontalAlignment = 'Left';
        break;
      case 'center':
        range.format.horizontalAlignment = 'Center';
        break;
      case 'right':
        range.format.horizontalAlignment = 'Right';
        break;
      case 'justify':
        range.format.horizontalAlignment = 'Justify';
        break;
    }
  }

  if (style.v_align) {
    switch (style.v_align) {
      case 'top':
        range.format.verticalAlignment = 'Top';
        break;
      case 'middle':
        range.format.verticalAlignment = 'Center';
        break;
      case 'bottom':
        range.format.verticalAlignment = 'Bottom';
        break;
    }
  }

  // Borders mapping
  const applyBorder = (borderName: "EdgeTop" | "EdgeBottom" | "EdgeLeft" | "EdgeRight", borderStyle: string) => {
    if (borderStyle === 'none') {
      range.format.borders.getItem(borderName).style = 'None';
      return;
    }
    
    const border = range.format.borders.getItem(borderName);
    
    // Default border color matching text color or dark gray
    border.color = style.fg_color || '#333333';
    
    switch (borderStyle) {
      case 'thin':
        border.style = 'Continuous';
        border.weight = 'Thin';
        break;
      case 'medium':
        border.style = 'Continuous';
        border.weight = 'Medium';
        break;
      case 'thick':
        border.style = 'Continuous';
        border.weight = 'Thick';
        break;
      case 'double':
        border.style = 'Double';
        border.weight = 'Medium';
        break;
      case 'dashed':
        border.style = 'Dash';
        border.weight = 'Thin';
        break;
      case 'dotted':
        border.style = 'Dot';
        border.weight = 'Thin';
        break;
    }
  };

  if (style.border_top) applyBorder('EdgeTop', style.border_top);
  if (style.border_bottom) applyBorder('EdgeBottom', style.border_bottom);
  if (style.border_left) applyBorder('EdgeLeft', style.border_left);
  if (style.border_right) applyBorder('EdgeRight', style.border_right);

  // Number format
  if (style.number_format) {
    range.numberFormat = [[style.number_format]];
  }
}
