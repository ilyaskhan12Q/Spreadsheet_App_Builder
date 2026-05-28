# Testing SAB

This file collects the exact commands to verify SAB locally.

## 1. Setup

```bash
cd /home/ilyaskhan/aj/spdshet/spreadsheet-app-builder
cp .env.example .env
source venv/bin/activate
pip install -r requirements.txt
```

If you plan to use Gemini:

```bash
pip install google-genai
```

## 2. Configure `.env`

Choose one provider:

```env
SAB_AI_PROVIDER=claude
SAB_ANTHROPIC_API_KEY=your_claude_key_here
```

Or:

```env
SAB_AI_PROVIDER=gemini
SAB_GEMINI_API_KEY=your_gemini_key_here
```

## 3. Validate the pipeline

Claude:

```bash
PYTHONPATH=. python cli/sab.py build "Create a simple invoice with subtotal" --provider claude --validate-only
```

Gemini:

```bash
PYTHONPATH=. python cli/sab.py build "Create a simple invoice with subtotal" --provider gemini --validate-only
```

## 4. Start LibreOffice for live render

```bash
libreoffice --calc --nologo --nodefault --accept="socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
```

## 5. Render live into Calc

Gemini live render:

```bash
PYTHONPATH=venv/lib/python3.13/site-packages:. python3 cli/sab.py build "Create a simple invoice with subtotal" --provider gemini --adapter uno
```

Claude live render:

```bash
PYTHONPATH=venv/lib/python3.13/site-packages:. python3 cli/sab.py build "Create a simple invoice with subtotal" --provider claude --adapter uno
```

## 6. LibreOffice smoke test

If the AI provider is rate-limited, render a known-good fixture directly:

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
