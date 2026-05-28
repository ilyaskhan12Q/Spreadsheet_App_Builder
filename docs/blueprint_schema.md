# Spreadsheet App Builder (SAB) Blueprint Schema

The JSON Blueprint is the single data contract between the AI layer and the rendering layer. This document serves as the full schema specification for the Blueprint.

---

## 1. Schema Reference

### `Blueprint` (Root Model)
| Field | Type | Required? | Description |
| :--- | :--- | :--- | :--- |
| `meta` | `Meta` | Yes | Global settings, grid configuration, column widths, row heights. |
| `regions` | `List[Region]` | Yes | High-level logical grouping of cells (headers, inputs, data tables). |
| `cells` | `List[Cell]` | Yes | The individual cells with values, formulas, validation, and styling. |
| `merges` | `List[MergeConfig]` | No | Ranges of cells to merge (default: `[]`). |
| `named_ranges` | `List[NamedRange]` | No | Named cell references (default: `[]`). |

---

### `Meta`
| Field | Type | Required? | Default | Description | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `app_type` | `AppType` (Enum) | Yes | - | Category: `pos`, `dashboard`, `invoice`, `other`. | `"pos"` |
| `title` | `str` | Yes | - | App/Spreadsheet title. | `"My Terminal"` |
| `description` | `str` | Yes | - | Brief overview of what the app does. | `"Records sales"` |
| `author` | `str` | No | `"SAB Engine"` | Creator identity. | `"John Doe"` |
| `version` | `str` | No | `"1.0.0"` | SemVer version. | `"1.1.0"` |
| `frozen_rows` | `int` | No | `0` | Frozen rows from top. | `1` |
| `frozen_cols` | `int` | No | `0` | Frozen columns from left. | `0` |
| `hide_gridlines` | `bool` | No | `false` | Hides default gridlines. | `true` |
| `col_widths` | `Dict[str, float]` | No | `{}` | Custom widths (Col Letter -> width). | `{"A": 15.0}` |
| `row_heights` | `Dict[int, float]` | No | `{}` | Custom heights (Row Number -> height). | `{"1": 25.0}` |

---

### `Region`
| Field | Type | Required? | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `region_id` | `str` | Yes | Unique ID of this region. | `"inputs"` |
| `type` | `RegionType` (Enum) | Yes | Region category: `header`, `input`, `output`, `data_table`, `chart_placeholder`, `kpi_card`. | `"input"` |
| `anchor` | `str` | Yes | Top-left cell reference. | `"A4"` |
| `size` | `Tuple[int, int]` | Yes | Dimensions as `(rows, cols)`. | `[5, 2]` |
| `title` | `str` | No | Display title for the region. | `"Form Inputs"` |
| `cell_ids` | `List[str]` | Yes | All cell addresses included in region. | `["A4", "B4", "A5", "B5"]` |

---

### `Cell`
| Field | Type | Required? | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `cell_id` | `str` | Yes | Cell coordinate in A1 notation. | `"B5"` |
| `value` | `Any` | No | Text, number, or boolean. | `12.50` |
| `formula` | `str` | No | Formula starting with `=`. | `"=B4*C4"` |
| `style` | `CellStyle` | No | Rendering styling. | `{ "bold": true }` |
| `validation` | `Validation` | No | Data validation constraints. | `{ "type": "list", "formula1": "Yes,No" }` |
| `event` | `Event` | No | Interactivity / macro mapping. | `{ "type": "button", "action": "submit" }` |

---

### `CellStyle`
| Field | Type | Required? | Default | Description | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `bg_color` | `str` | No | `None` | Hex code. | `"#4A148C"` |
| `fg_color` | `str` | No | `None` | Hex code. | `"#FFFFFF"` |
| `font_size` | `float` | No | `10.0` | Font size in points. | `12.0` |
| `bold` | `bool` | No | `false` | Bold font weight. | `true` |
| `italic` | `bool` | No | `false` | Italic font style. | `false` |
| `border_top` | `BorderStyle` | No | `"none"` | Border style: `none`, `thin`, `medium`, `thick`, `double`, `dashed`, `dotted`. | `"thin"` |
| `border_bottom`| `BorderStyle` | No | `"none"` | Border style. | `"double"` |
| `border_left`  | `BorderStyle` | No | `"none"` | Border style. | `"none"` |
| `border_right` | `BorderStyle` | No | `"none"` | Border style. | `"none"` |
| `number_format`| `str` | No | `None` | Formatting pattern. | `"$#,##0.00"` |
| `h_align` | `HAlign` | No | `"left"` | Align: `left`, `center`, `right`, `justify`. | `"center"` |
| `v_align` | `VAlign` | No | `"middle"` | Align: `top`, `middle`, `bottom`. | `"middle"` |

---

### `Validation`
| Field | Type | Required? | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `type` | `str` | Yes | Type of validation: `list`, `decimal`, `whole`, `date`, `text_length`. | `"list"` |
| `formula1` | `str` | Yes | List items or boundary expression. | `"Cash,Card"` |
| `allow_blank` | `bool` | No | If cell allows blank values (default `true`). | `false` |
| `error_message`| `str` | No | Custom warning shown on error. | `"Select method"` |

---

### `Event`
| Field | Type | Required? | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `type` | `str` | No | Default `"button"`. | `"button"` |
| `action` | `str` | Yes | Macro name triggered on click. | `"submit_invoice"` |

---

### `MergeConfig`
| Field | Type | Required? | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `range` | `str` | Yes | Merged range in A1 notation. | `"A1:E2"` |

---

### `NamedRange`
| Field | Type | Required? | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `name` | `str` | Yes | Unique range name (no spaces). | `"TotalRevenue"` |
| `range` | `str` | Yes | Range in A1 notation. | `"Sheet1!B10"` |

---

## 2. How the AI Uses This Schema

The system uses Pydantic's JSON schema serialization to inject this model schema directly into the selected model's system prompt instructions.
When a user provides a prompt:
1. The **ContextScanner** parses any existing spreadsheet attributes.
2. The **AITranslator** passes the user prompt + context + system prompt (with schema) to the selected provider.
3. The provider generates a raw JSON string matching the blueprint schema.
4. **BlueprintValidator** runs both structural Pydantic validation and semantic logic checks.
5. If errors are encountered, they are piped back into the provider's context for auto-correction.

---

## 3. Writing Prompts that Produce Good Blueprints

To ensure high-quality spreadsheet apps, structure prompts with the following details:
1. **App Intent:** Specify the app type (e.g., POS terminal, Dashboard).
2. **Visual Hierarchy:** Describe layout placements (e.g., "Place the header in A1:D2, followed by client inputs in A4:B6").
3. **Interactivity:** State which cell should act as a button and what action it triggers (e.g., "A green button in D4 named 'Save Invoice' that runs macro 'save_data'").
4. **Formulas & Constraints:** Detail calculation logic explicitly (e.g., "Calculate tax in E15 as 10% of taxable items in E10:E12").

---

## 4. Prompt → Blueprint Walkthrough Example

### Input User Prompt:
> Create a minimalist discount calculator. Row 1 (A1:C1) is a blue header titled "Discount Calculator". Inputs are at A3 ("Original Price") and A4 ("Discount Rate" as percentage). Output is at A6 ("Final Price") with a formula subtracting the discount from the original price. The gridlines should be hidden.

### Generated Blueprint Output:
```json
{
  "meta": {
    "app_type": "other",
    "title": "Discount Calculator",
    "description": "Minimalist calculator to compute discounted price.",
    "hide_gridlines": true
  },
  "regions": [
    {
      "region_id": "header",
      "type": "header",
      "anchor": "A1",
      "size": [1, 3],
      "cell_ids": ["A1", "B1", "C1"]
    },
    {
      "region_id": "inputs",
      "type": "input",
      "anchor": "A3",
      "size": [2, 2],
      "cell_ids": ["A3", "B3", "A4", "B4"]
    },
    {
      "region_id": "outputs",
      "type": "output",
      "anchor": "A6",
      "size": [1, 2],
      "cell_ids": ["A6", "B6"]
    }
  ],
  "cells": [
    {
      "cell_id": "A1",
      "value": "Discount Calculator",
      "style": {
        "bg_color": "#0288D1",
        "fg_color": "#FFFFFF",
        "bold": true,
        "h_align": "center"
      }
    },
    {
      "cell_id": "A3",
      "value": "Original Price",
      "style": { "bold": true }
    },
    {
      "cell_id": "B3",
      "value": 100.0,
      "style": { "number_format": "$#,##0.00" }
    },
    {
      "cell_id": "A4",
      "value": "Discount Rate",
      "style": { "bold": true }
    },
    {
      "cell_id": "B4",
      "value": 0.15,
      "style": { "number_format": "0.0%" }
    },
    {
      "cell_id": "A6",
      "value": "Final Price",
      "style": { "bold": true, "bg_color": "#E1F5FE" }
    },
    {
      "cell_id": "B6",
      "formula": "=B3*(1-B4)",
      "style": { "bold": true, "bg_color": "#E1F5FE", "number_format": "$#,##0.00" }
    }
  ],
  "merges": [
    { "range": "A1:C1" }
  ]
}
```
