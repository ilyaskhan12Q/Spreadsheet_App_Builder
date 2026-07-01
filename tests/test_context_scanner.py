import os
import tempfile

import openpyxl

from core.scanner.context_builder import ContextScanner


def test_context_scanner_xlsx_parsing():
    # 1. Create a temporary Excel file with dummy headers and data
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "GroceryStore"

        # Add headers
        ws.append(["Product ID", "Product Name", "Retail Price", "Inventory Count"])
        # Add some data rows
        ws.append(["P101", "Apple", 1.50, 100])
        ws.append(["P102", "Banana", 0.80, 150])
        ws.append(["P103", "Orange", 1.20, 80])

        wb.save(tmp_path)

        # 2. Run ContextScanner
        scanner = ContextScanner()
        context = scanner.build_context(tmp_path)

        # 3. Assertions
        assert "GroceryStore" in context.sheet_names
        assert context.used_range == "A1:D4"
        assert context.headers == ["Product ID", "Product Name", "Retail Price", "Inventory Count"]
        assert len(context.data_sample) == 3
        assert context.data_sample[0]["Product Name"] == "Apple"
        assert context.data_sample[1]["Inventory Count"] == 150

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
