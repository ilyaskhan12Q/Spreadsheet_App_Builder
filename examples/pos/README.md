# Point of Sale (POS) Terminal Example

This example demonstrates how to build a basic transaction processing system using the SpreadsheetAppBuilder (SAB) engine.

## Layout & Regions

### 1. Header Region (`header_region`)
* **Range:** `A1:E2` (merged)
* **Style:** Sleek indigo blue background (`#1A237E`) with large bold white text.
* **Purpose:** Sets the visual context and branding for the application.

### 2. Transaction Details Input Region (`input_region`)
* **Range:** `A4:B8`
* **Purpose:** Captures details for the current transaction:
  * **Product Dropdown (`B5`):** Restricts selection to `Coffee`, `Tea`, `Muffin`, or `Croissant` using data validation.
  * **Quantity (`B6`):** Stores number of items, constrained by validation to values `1` or greater.
  * **Unit Price (`B7`):** Direct numeric input formatted as currency (`$#,##0.00`).
  * **Payment Method (`B8`):** Restricts payment selection to `Cash`, `Card`, or `Mobile` via a dropdown list.

### 3. Summary Output Region (`output_region`)
* **Range:** `A10:B10`
* **Style:** Highlights totals in a soft yellow background (`#FFF9C4`) with double-line accounting underline styles.
* **Purpose:** Calculates the order's total pricing:
  * **Total Amount (`B10`):** Formula computes quantity times price (`=B6*B7`).

### 4. Actions Region (`action_region`)
* **Range:** `D5:E5` (merged button)
* **Style:** Green button style (`#2E7D32`) with white text and thin borders.
* **Event Action (`submit_order`):** Triggers the `submit_order` basic macro or backend endpoint callback, validating the selected dropdown values and writing the transaction to a database.
