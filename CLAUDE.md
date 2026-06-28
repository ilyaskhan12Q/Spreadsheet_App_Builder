# CLAUDE.md — SpreadsheetAppBuilder (SAB)

## Architecture

SAB is an open-source engine that turns a text prompt into a working spreadsheet app
(POS, dashboard, invoice, tracker, etc).

### Pipeline

```
User prompt + design prefs + provider choice
    → AI Provider (Gemini default / Claude / OpenAI, user's own key)
      generates a small semantic "App Spec" (sections, fields, actions)
    → Blueprint Compiler (pure code, NO AI) resolves App Spec
      + Design Tokens + Region Template Library
      → full JSON Blueprint (exact cells, styles, formulas, merges)
    → Validator (Pydantic) checks bounds/conflicts
    → Renderers consume the SAME blueprint:
        - xlsx_writer.py (PRIMARY, openpyxl) — produces a real .xlsx
        - uno_macro.py (OPTIONAL) — adds LibreOffice Basic macros/buttons
        - vba_layer.py (OPTIONAL) — adds Excel VBA macros/buttons
```

### Directory Structure

```
spreadsheet-app-builder/
├── core/
│   ├── blueprint.py            # Universal Blueprint schema (Pydantic v2)
│   ├── app_spec.py             # Small semantic schema, AI output target
│   ├── ai/
│   │   ├── providers/
│   │   │   ├── base.py         # AIProvider ABC
│   │   │   ├── gemini_provider.py
│   │   │   ├── claude_provider.py
│   │   │   ├── openai_provider.py
│   │   │   └── factory.py
│   │   └── prompt_templates/
│   ├── compiler/
│   │   ├── app_spec_to_blueprint.py
│   │   ├── region_templates/   # Reusable layout snippets per app_type
│   │   └── design_tokens.py
│   └── validator/
│       ├── schema.py
│       └── constraint_checker.py
├── renderers/
│   ├── xlsx_writer.py          # PRIMARY
│   ├── uno_macro.py            # OPTIONAL
│   └── vba_layer.py            # OPTIONAL
├── cli/
│   └── sab.py
├── web/                        # React + Vite (GitHub Pages)
├── tests/
└── ...
```

## Critical Rules

### 1. AI Layer Never Outputs Coordinates or Colors Directly

The AI generates a small semantic **App Spec** describing WHAT the app needs.
A deterministic **Blueprint Compiler** converts that into exact cell coordinates,
hex colors, and layout. This separation exists because LLMs are unreliable at
spatial precision. **Never violate this boundary.**

### 2. Every Renderer Change Needs a Corresponding Test

No renderer code ships without a test that verifies its output. For xlsx_writer,
this means openpyxl read-back assertions.

### 3. No Secrets Committed — Ever

API keys are user-supplied at runtime (CLI flag, env var, or web form).
Never hardcoded, never committed, never logged, never transmitted to any
SAB-controlled server. The `.env` file is in `.gitignore`.

### 4. Commit Convention

Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.

### 5. Commands

```bash
# Tests
PYTHONPATH=. pytest tests/ -v

# Lint
ruff check core/ cli/ renderers/ tests/

# Type check
mypy core/ cli/ renderers/ --ignore-missing-imports

# Web (once set up)
cd web && npm run dev
cd web && npm run build
```

### 6. LibreOffice is Primary Target

The .xlsx output must open correctly in both LibreOffice Calc and MS Excel.
Live macro layers (UNO/VBA) are optional add-ons, not the core deliverable.

### 7. Formula Injection Prevention

The compiler must reject dangerous formulas in user-influenced cells:
no `=HYPERLINK`, `=IMPORTXML`, `=IMPORTDATA`, or similar injection vectors.
