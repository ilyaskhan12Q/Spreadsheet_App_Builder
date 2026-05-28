import logging
from typing import Any
from adapters.base import AbstractAdapter, AdapterError
from core.blueprint import Blueprint
from adapters.uno.style_mapper import map_cell_style
from adapters.uno.macro_runner import insert_macro_stub, assign_macro_to_cell

logger = logging.getLogger("sab.uno_renderer")


class UNOAdapter(AbstractAdapter):
    def render(self, blueprint: Blueprint, spreadsheet_handle: Any = None) -> None:
        """
        Orchestrates rendering the blueprint in LibreOffice Calc via UNO.
        spreadsheet_handle is the LibreOffice document component (XComponent).
        """
        if not spreadsheet_handle:
            raise AdapterError("spreadsheet_handle (LibreOffice XComponent document) is required.")

        doc = spreadsheet_handle
        try:
            # Resolve active sheet
            sheet = doc.getCurrentController().getActiveSheet()
        except Exception as e:
            try:
                sheet = doc.getSheets().getByIndex(0)
            except Exception as e_inner:
                raise AdapterError(f"Could not access spreadsheet sheets: {e_inner}") from e

        # a. Hide gridlines
        self.hide_gridlines(doc, blueprint.meta.hide_gridlines)

        # b. Freeze panes
        self.freeze_panes(doc, blueprint.meta.frozen_rows, blueprint.meta.frozen_cols)

        # c. Render regions (sets column widths / row heights and merges)
        self.render_regions(sheet, blueprint)

        # d. Render cells (values, formulas, validations, styles)
        self.render_cells(doc, sheet, blueprint)

        # e. Render events (wires buttons/dropdowns/macros)
        self.render_events(doc, sheet, blueprint)

    def hide_gridlines(self, doc: Any, hide: bool) -> None:
        """Hides or shows gridlines in the active controller."""
        try:
            controller = doc.getCurrentController()
            if hasattr(controller, "ShowGrid"):
                controller.ShowGrid = not hide
            else:
                # Fallback to setting via properties if supported
                controller.setPropertyValue("ShowGrid", not hide)
            logger.info(f"Set ShowGrid to {not hide}")
        except Exception as e:
            logger.warning(f"Could not configure gridlines view: {e}")

    def freeze_panes(self, doc: Any, frozen_rows: int, frozen_cols: int) -> None:
        """Freezes rows and columns in the active controller."""
        if frozen_rows <= 0 and frozen_cols <= 0:
            return
        try:
            controller = doc.getCurrentController()
            # freezeAtPosition takes (columns_to_freeze, rows_to_freeze)
            controller.freezeAtPosition(frozen_cols, frozen_rows)
            logger.info(f"Frozen rows: {frozen_rows}, cols: {frozen_cols}")
        except Exception as e:
            logger.warning(f"Could not configure pane freeze: {e}")

    def render_regions(self, sheet: Any, blueprint: Blueprint) -> None:
        """Sets row heights and column widths and performs cell merges."""
        # 1. Custom column widths
        for col_letter, width in blueprint.meta.col_widths.items():
            try:
                col_obj = sheet.getColumns().getByName(col_letter)
                # Convert width (assumed in standard characters/points) to Calc's 1/100th mm
                # 1 point = 35.278 of 1/100mm
                col_obj.Width = int(width * 35.278)
            except Exception as e:
                logger.warning(f"Could not set width for column '{col_letter}': {e}")

        # 2. Custom row heights
        for row_num_str, height in blueprint.meta.row_heights.items():
            try:
                row_idx = int(row_num_str) - 1
                row_obj = sheet.getRows().getByIndex(row_idx)
                row_obj.Height = int(height * 35.278)
            except Exception as e:
                logger.warning(f"Could not set height for row '{row_num_str}': {e}")

        # 3. Handle merges
        for merge_cfg in blueprint.merges:
            try:
                range_obj = sheet.getCellRangeByName(merge_cfg.range)
                range_obj.merge(True)
                logger.info(f"Merged range: {merge_cfg.range}")
            except Exception as e:
                logger.warning(f"Could not merge range '{merge_cfg.range}': {e}")

    def render_cells(self, doc: Any, sheet: Any, blueprint: Blueprint) -> None:
        """Populates values, formulas, data validation, and cell styles."""
        for cell in blueprint.cells:
            try:
                cell_obj = sheet.getCellRangeByName(cell.cell_id)

                # Set formula or value
                if cell.formula:
                    cell_obj.setFormula(cell.formula)
                elif cell.value is not None:
                    if isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool):
                        cell_obj.setValue(cell.value)
                    elif isinstance(cell.value, bool):
                        cell_obj.setValue(1 if cell.value else 0)
                    else:
                        cell_obj.setString(str(cell.value))

                # Apply data validation
                if cell.validation:
                    self._apply_validation(cell_obj, cell.validation)

                # Apply cell styles
                if cell.style:
                    uno_props = map_cell_style(cell.style)
                    for prop_name, prop_val in uno_props.items():
                        try:
                            if prop_val is not None:
                                cell_obj.setPropertyValue(prop_name, prop_val)
                        except Exception:
                            # Direct assignment fallback if setPropertyValue fails
                            try:
                                setattr(cell_obj, prop_name, prop_val)
                            except Exception:
                                pass

                    # Apply custom number formatting if defined
                    if cell.style.number_format:
                        self._apply_number_format(doc, cell_obj, cell.style.number_format)

            except Exception as e:
                logger.warning(f"Error rendering cell {cell.cell_id}: {e}")

    def _apply_validation(self, cell_obj: Any, validation: Any) -> None:
        """Applies data validation constraints to a UNO Cell."""
        try:
            valid_obj = cell_obj.Validation
            
            # ValidationType mapping: 
            # 0=ANY, 1=CUSTOM, 2=WHOLE, 3=DECIMAL, 4=DATE, 5=TEXT_LEN, 6=LIST
            type_map = {
                "list": 6,
                "whole": 2,
                "decimal": 3,
                "date": 4,
                "text_length": 5
            }
            v_type = type_map.get(validation.type.lower(), 0)
            valid_obj.Type = v_type
            valid_obj.Formula1 = validation.formula1
            valid_obj.AllowEmptyCell = validation.allow_blank
            
            if validation.error_message:
                valid_obj.ErrorMessage = validation.error_message
                valid_obj.ShowErrorMessage = True
                valid_obj.ErrorAlertStyle = 1  # STOP style
                
            cell_obj.Validation = valid_obj
        except Exception as e:
            logger.warning(f"Could not apply data validation: {e}")

    def _apply_number_format(self, doc: Any, cell_obj: Any, format_str: str) -> None:
        """Applies number format to cell_obj via doc NumberFormats supplier."""
        try:
            num_formats = doc.getNumberFormats()
            # Construct a default/dummy locale
            if hasattr(doc, "CharLocale"):
                locale = doc.CharLocale
            else:
                # Mock or build empty locale struct
                try:
                    import uno  # type: ignore
                    locale = uno.createUnoStruct("com.sun.star.lang.Locale")
                except Exception:
                    class DummyLocale:
                        Language = "en"
                        Country = "US"
                        Variant = ""
                    locale = DummyLocale()
            
            key = num_formats.queryKey(format_str, locale, False)
            if key == -1:
                key = num_formats.addNew(format_str, locale)
            cell_obj.NumberFormat = key
        except Exception as e:
            logger.warning(f"Could not apply number format '{format_str}': {e}")

    def render_events(self, doc: Any, sheet: Any, blueprint: Blueprint) -> None:
        """Wires up buttons or interactive elements to macro triggers."""
        for cell in blueprint.cells:
            if cell.event and cell.event.type == "button":
                try:
                    cell_obj = sheet.getCellRangeByName(cell.cell_id)
                    # Insert stub macro into the document Standard basic library
                    insert_macro_stub(doc, cell.event.action)
                    # Assign macro dispatcher VND script link to the cell
                    assign_macro_to_cell(doc, sheet, cell_obj, cell.event)
                except Exception as e:
                    logger.warning(f"Could not bind macro event for cell {cell.cell_id}: {e}")
