# Professional Invoice Generator Example

This example demonstrates how to build a flexible billing sheet containing customer information, itemized services, tax calculations, and totals.

## Layout & Regions

### 1. Invoice Header (`invoice_header`)
* **Range:** `A1:E2` (merged)
* **Style:** Purple header background (`#4A148C`) with high-contrast white text.

### 2. Client Info Inputs (`client_info`)
* **Range:** `A4:B6`
* **Purpose:** Stores core invoice attributes (Client Name, Invoice Date, Invoice Reference number).

### 3. Line Items Table (`line_items`)
* **Range:** `A9:E13`
* **Headers:** Description, Quantity, Unit Price, Taxable status, and Row Total.
* **Logic:** Computes row total for each service line item (e.g. `=B10*C10`).
* **Dropdowns:** "Taxable (Y/N)" restricted to `Y` or `N` list options.

### 4. Totals Summary (`totals_region`)
* **Range:** `D14:E16`
* **Calculations:**
  * **Subtotal (`E14`):** Summarizes all row totals via `=SUM(E10:E12)`.
  * **Tax (`E15`):** Dynamically applies 8.25% tax ONLY to lines marked as taxable using `=SUMIF(D10:D12,"Y",E10:E12)*0.0825`.
  * **Total Due (`E16`):** Sums Subtotal and Tax via `=E14+E15`.
