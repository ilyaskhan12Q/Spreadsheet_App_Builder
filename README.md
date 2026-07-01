<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+"/>
  <img src="https://img.shields.io/badge/TypeScript-5.4+-3178C6?logo=typescript&logoColor=white" alt="TypeScript"/>
  <img src="https://img.shields.io/badge/AI-Claude%20Sonnet-blueviolet" alt="Claude Sonnet"/>
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"/>
</p>

# Spreadsheet App Builder (SAB)

> **Describe a spreadsheet application in plain English. Get a fully formatted, validated, interactive workbook in LibreOffice Calc or Microsoft Excel — powered by Claude or Gemini.**

SAB is an open-source engine that translates natural-language prompts into structured JSON blueprints, validates them against a strict Pydantic / Zod schema, and renders them into real spreadsheet documents with cell values, formulas, styles, data validations, merged regions, and macro-driven button events.

---

## Quick Verify

If you want the shortest path to prove the project works end to end:

1. Install the package in editable mode: `pip install -e .`
2. Copy `/.env.example` to `.env` and set `SAB_AI_PROVIDER` plus the matching API key.
3. Run `sab build "Create a simple invoice with subtotal" --validate-only`.
4. Generate a real Excel workbook:
   ```bash
   sab build "Create a simple invoice with subtotal" --provider gemini --adapter xlsx --output invoice.xlsx
   ```
5. Open `invoice.xlsx` in Microsoft Excel or ONLYOFFICE Desktop Editors!
6. If Gemini is rate-limited, use the direct LibreOffice smoke test in the live render section below.
7. For the full command list, see [TESTING.md](TESTING.md).

---

## Architecture

```
User Prompt
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ ContextScanner│────▶│ AITranslator │────▶│  Validator    │────▶│   Adapter    │
│  (Stage 1)   │     │  (Stage 2)   │     │  (Stage 3)   │     │  (Stage 4)   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
  SpreadsheetContext    Raw JSON            Blueprint Model      Rendered Sheet
                        ▲     │
                        │     ▼
                      AI Provider API
                    (claude-sonnet-4-20250514)
```

**The JSON Blueprint is the ONLY data contract between the AI layer and the rendering layer.** No agent writes directly to cells. No agent calls the AI provider from the renderer.

---

## Repository Layout

```
spreadsheet-app-builder/
├── core/                       # Python core pipeline
│   ├── blueprint.py            # Pydantic v2 schema (Blueprint, Cell, CellStyle, …)
│   ├── pipeline.py             # End-to-end orchestrator
│   ├── scanner/
│   │   └── context_builder.py  # Scans existing sheet state for prompt injection
│   ├── ai/
│   │   ├── translator.py       # Claude/Gemini API integration + retry logic
│   │   └── system_prompt.txt   # System prompt template with JSON schema
│   └── validator/
│       ├── schema.py           # Pydantic parse + constraint bridge
│       └── constraint_checker.py  # Bounds, merge-conflict, formula-syntax checks
│
├── adapters/
│   ├── base.py                 # AbstractAdapter interface
│   ├── uno/                    # LibreOffice Calc renderer (python-uno)
│   │   ├── renderer.py         # UNOAdapter — full cell/style/validation/event rendering
│   │   ├── style_mapper.py     # CellStyle → UNO property mapping
│   │   ├── macro_runner.py     # Basic macro stub injection + HYPERLINK wiring
│   │   └── install.py          # Installs SAB macros into LO user profile
│   └── officejs/               # Microsoft Excel add-in (TypeScript + React)
│       ├── src/
│       │   ├── blueprint.ts    # Zod schema (mirrors core/blueprint.py)
│       │   ├── renderer.ts     # ExcelRenderer — Office.js API calls
│       │   ├── styleMapper.ts  # CellStyle → Excel format mapping
│       │   └── taskpane.tsx    # React task pane UI with progress stepper
│       ├── manifest.xml        # Office Add-in manifest
│       ├── taskpane.html       # Entry HTML for the add-in
│       ├── package.json
│       ├── tsconfig.json
│       └── vite.config.ts
│
├── cli/
│   ├── sab.py                  # Click CLI (sab build "…" --adapter uno)
│   └── server.py               # FastAPI backend for the Office.js task pane
│
├── tests/
│   ├── test_core_pipeline.py   # 8 unit tests — validation, constraints, translator
│   ├── test_renderer_uno.py    # Mocked UNO adapter integration test
│   └── fixtures/               # 3 gold-standard blueprints (POS, Dashboard, Invoice)
│
├── examples/                   # Human-readable examples with README + blueprint.json
│   ├── pos/
│   ├── dashboard/
│   └── invoice/
│
├── docs/
│   ├── blueprint_schema.md     # Full schema reference
│   └── adapter_guide.md        # UNO + Office.js setup & troubleshooting
│
├── .github/workflows/ci.yml   # GitHub Actions CI (pytest + ruff + mypy + vitest)
├── pyproject.toml              # Poetry config with sab + sab-server entry points
├── requirements.txt
└── .gitignore
```

---

## Quick Start

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Core pipeline |
| Node.js | 20+ | Office.js adapter only |
| LibreOffice | 7.5+ | UNO adapter only |
| `python3-uno` | system package | Needed for live LibreOffice rendering |
| Anthropic API key | — | `SAB_ANTHROPIC_API_KEY` env var |
| Gemini API key | — | `SAB_GEMINI_API_KEY` or `GEMINI_API_KEY` env var |

### 1. Clone & install

```bash
git clone https://github.com/ilyaskhan12Q/Spreadsheet_App_Builder.git
cd spreadsheet-app-builder

python3 -m venv venv && source venv/bin/activate
pip install -e .
# Only needed if you plan to use Gemini
pip install google-genai
```

### 2. Set your API key

Or copy `.env.example` to `.env` and fill in the provider you want to use. The CLI and API load `.env` automatically.

```bash
# Claude
export SAB_ANTHROPIC_API_KEY="sk-ant-…"

# Gemini
export SAB_GEMINI_API_KEY="AIza…"
```

### 3. Generate a spreadsheet app (CLI)

```bash
# Validate-only mode (outputs blueprint JSON, no rendering)
sab build "Create a simple invoice with subtotal" --validate-only

# Use Gemini instead of Claude
sab build "Create a simple invoice with subtotal" --provider gemini --validate-only
```

### 4. Live LibreOffice render

Start Calc in listening mode first:

```bash
libreoffice --calc --nologo --nodefault --accept="socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
```

Then run a real render into the open workbook window:

```bash
PYTHONPATH=venv/lib/python3.13/site-packages:. python3 cli/sab.py build "Create a simple invoice with subtotal" --provider gemini --adapter uno
```

If you want to verify the LibreOffice connection without waiting on the AI provider, render a known-good fixture directly:

```bash
PYTHONPATH=venv/lib/python3.13/site-packages:. python3 - <<'PY'
from pathlib import Path
import uno
from core.validator.schema import BlueprintValidator
from adapters.uno.renderer import UNOAdapter

raw_json = Path('tests/fixtures/invoice_blueprint.json').read_text()
blueprint = BlueprintValidator().validate(raw_json)

local_context = uno.getComponentContext()
resolver = local_context.ServiceManager.createInstanceWithContext(
    'com.sun.star.bridge.UnoUrlResolver', local_context
)
ctx = resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')
smgr = ctx.ServiceManager
desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
doc = desktop.loadComponentFromURL('private:factory/scalc', '_blank', 0, ())
UNOAdapter().render(blueprint, doc)
print('render-complete')
PY
```

### 5. Office.js adapter (Excel)

```bash
cd adapters/officejs
npm install
npm run dev          # Starts task pane on localhost:3000
```

Then sideload `manifest.xml` into Excel — see [Adapter Guide](docs/adapter_guide.md#2-microsoft-excel-adapter-officejs).

---

## Running Tests

```bash
# Python (core + UNO adapter)
PYTHONPATH=. pytest                # 17 tests

# Linting & type-checking
ruff check core cli adapters/uno   # zero errors
mypy core cli adapters/uno         # zero errors

# TypeScript (Office.js adapter)
cd adapters/officejs && npm test   # 1 test suite
```

---

## Blueprint Schema at a Glance

Every blueprint is a JSON object with this top-level shape:

```jsonc
{
  "meta": {
    "app_type": "pos | dashboard | invoice | other",
    "title": "…",
    "description": "…",
    "frozen_rows": 2,
    "col_widths": { "A": 15.0, "B": 20.0 },
    "hide_gridlines": true
  },
  "regions": [
    { "region_id": "header", "type": "header", "anchor": "A1", "size": [2, 5], "cell_ids": ["A1"] }
  ],
  "cells": [
    { "cell_id": "A1", "value": "Title", "style": { "bg_color": "#1A237E", "bold": true } },
    { "cell_id": "B5", "formula": "=SUM(B2:B4)", "validation": { "type": "decimal", "formula1": ">=0" } }
  ],
  "merges": [{ "range": "A1:E2" }],
  "named_ranges": [{ "name": "Total", "range": "B10" }]
}
```

Full reference → [docs/blueprint_schema.md](docs/blueprint_schema.md)

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Pydantic v2 as the single source of truth** | Generates JSON Schema for the system prompt _and_ validates AI output in one place |
| **Retry loop with error feedback** | When the provider's JSON fails validation, the error is fed back as a user message for self-correction (max 2 retries) |
| **Hex-only colours, `=`-prefixed formulas** | Eliminates ambiguity; both UNO and Office.js adapters consume these deterministically |
| **No direct cell writes from AI** | The renderer is a pure function of the Blueprint — makes testing, caching, and replay trivial |
| **Fallback stubs for `python-uno`** | Allows the full test suite to run on CI without a LibreOffice installation |

---

## Examples

| App | Preview | Key features |
|-----|---------|--------------|
| **Point of Sale** | [examples/pos/](examples/pos/) | Product dropdown, quantity input, auto-calculated total, submit button with macro |
| **KPI Dashboard** | [examples/dashboard/](examples/dashboard/) | Revenue/expense cards, summary formulas, conditional colour coding |
| **Invoice Generator** | [examples/invoice/](examples/invoice/) | Client fields, line-item table, tax calculation, merge-based header layout |

---

## Contributing

1. Fork → branch → commit → PR
2. All PRs must pass CI (`pytest`, `ruff`, `mypy`, `vitest`)
3. New adapters go in `adapters/<name>/`
4. New fixture blueprints go in `tests/fixtures/`

---

## License

MIT — see [LICENSE](LICENSE) for details.
