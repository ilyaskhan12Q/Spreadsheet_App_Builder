# Executive KPI Dashboard Example

This example demonstrates how to create a read-only corporate KPI dashboard featuring summary cards, raw data tables, and a visual placeholder for charts.

## Layout & Regions

### 1. Main Header (`dashboard_header`)
* **Range:** `A1:K1` (merged)
* **Style:** Bold text on dark gray background (`#212121`).
* **Settings:** The top row is locked in place using `frozen_rows: 1`.

### 2. KPI Cards
Each card uses a distinct 2x2 grid to represent metrics with a clear header label and a large metric value.
* **Total Sales Card (`kpi_card_1` at `A2:B3`):** Reflects the overall revenue amount (`$15,420.50`).
* **Transactions Card (`kpi_card_2` at `C2:D3`):** Counts total orders (`320`).
* **Average Order Value Card (`kpi_card_3` at `G2:H3`):** Uses a formula (`=A3/C3`) to divide total sales by order count.
* **Refund Rate Card (`kpi_card_4` at `I2:J3`):** Shows percent of returned orders (`1.5%`).

### 3. Recent Sales Transactions (`sales_data_table`)
* **Range:** `A6:E11`
* **Style:** Slate headers (`#37474F`) with white text.
* **Purpose:** Displays itemized historical sales rows.
  * **Totals Row (`A11:E11`):** Row totals computed using `=SUM(C7:C10)` for quantity and `=SUM(E7:E10)` for revenue.

### 4. Chart Visualizer (`chart_region`)
* **Range:** `G6:K11` (merged)
* **Style:** Visual mockup containing border outlines and placeholder tag `[ VISUAL SALES TREND CHART ]` representing where chart objects are positioned.
* **Purpose:** Reserves space for a dashboard chart rendering logic.
