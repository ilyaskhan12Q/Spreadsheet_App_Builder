# Spreadsheet App Builder (SAB) Adapter Guide

This guide details the rendering adapters available in SAB for LibreOffice Calc (UNO) and Microsoft Excel (Office.js).

---

## 1. LibreOffice Calc Adapter (UNO)

The UNO (Universal Network Objects) adapter bridges the Python core pipeline directly into a running instance of LibreOffice Calc.

### How the UNO Layer Works

LibreOffice exposes a runtime component model called UNO. Through python-uno, SAB can interact with Calc workbooks, worksheets, columns, rows, and cells. The process is as follows:

1. **Connection:** SAB connects to a LibreOffice instance listening on a local port (e.g. port `2002`) or runs as a macro inside the LibreOffice process context.
2. **Document Retrieval:** Reaches the active sheet via the current controller (`doc.getCurrentController().getActiveSheet()`).
3. **Layout formatting:** Sets column widths, row heights, and merges cell ranges based on the region bounds defined in the blueprint.
4. **Cell rendering:** Populates cells with raw values, formulas (prefixed with `=`), data validation rules, and cell styles (font, borders, alignment, number formats).
5. **Interactive features:** When a cell has an event configured (such as a click event on a button), the adapter writes a Basic macro stub into the document's `Standard` library and maps a `HYPERLINK` call to dispatch it.

### How to Run SAB Inside LibreOffice

To use the UNO adapter, you must run LibreOffice in listening mode or load the macro stubs:

#### Step 1: Start LibreOffice in Listening Mode
Start Calc from the command line, enabling the socket connection port `2002`:
```bash
libreoffice --calc --nologo --nodefault --accept="socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
```

#### Step 2: Install SAB Macros
Install the helper macro modules into your local LibreOffice user profile:
```bash
python3 adapters/uno/install.py
```

#### Step 3: Run the CLI Builder
If you want to render the workbook from the AI pipeline, use the repo venv packages plus the system Python that can see `uno`:
```bash
PYTHONPATH=venv/lib/python3.13/site-packages:. python3 cli/sab.py build "Create a simple invoice with subtotal" --provider gemini --adapter uno
```

If you only want to verify the LibreOffice render path, load a known-good blueprint directly:
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

#### Step 4: Run the CLI Builder
Execute the SAB build command to construct your app:
```bash
PYTHONPATH=. python cli/sab.py build "Create a simple invoice with subtotal" --adapter uno
```

### Common Errors and Fixes

#### Error: `No module named 'uno'`
* **Cause:** The `uno` library is not installed in your active Python environment. Python-uno is typically distributed via system package managers.
* **Fix (Ubuntu/Debian):**
  ```bash
  sudo apt-get install python3-uno
  ```
  And make sure your virtual environment can access system packages, or run SAB using the system python with `PYTHONPATH=venv/lib/python3.13/site-packages:. python3 ...`.

#### Error: `Connection refused`
* **Cause:** LibreOffice is not running or is not listening on the expected socket port.
* **Fix:** Verify that the command `libreoffice --accept="..."` is running and that no firewall is blocking port `2002`.

---

## 2. Microsoft Excel Adapter (Office.js)

The `officejs` adapter implements a TypeScript-based rendering layer that communicates with Microsoft Excel via the Office Add-ins JavaScript API.

### How the Task Pane Communicates with the Python Backend

```
┌──────────────────┐               POST /api/build               ┌────────────────────┐
│  React Task Pane │ ──────────────────────────────────────────> │ SAB Python Backend │
│  (Office.js UI)  │ <────────────────────────────────────────── │ (AITranslator API) │
└──────────────────┘               Blueprint JSON                └────────────────────┘
```

1. **User Prompt Submission:** The user types a description of their app in the React textarea and clicks **Build App**.
2. **REST Request:** The task pane sends a POST request with the prompt to the SAB local backend (`http://localhost:8000/api/build`).
3. **AI Translation:** The backend translates the prompt, validates it, and returns the compiled JSON Blueprint.
4. **Validation:** The task pane validates the returned blueprint using Zod schemas (`src/blueprint.ts`).
5. **Excel.run execution:** The `ExcelRenderer` parses the blueprint and makes transactional Office.js API calls to modify the active worksheet.

### Build and Dev Commands

Navigate to `adapters/officejs/` to run these commands:

* **Install dependencies:**
  ```bash
  npm install
  ```
* **Start dev server (Vite):**
  ```bash
  npm run dev
  ```
  This starts the task pane frontend on `https://localhost:3000`.
* **Run Vitest unit tests:**
  ```bash
  npm run test
  ```
* **Build production bundles:**
  ```bash
  npm run build
  ```

### How to Sideload the Add-in in Excel

#### Sideloading in Excel on the Web:
1. Open [Office.com](https://office.com) and create a new Excel workbook.
2. Select the **Insert** tab, then choose **Office Add-ins**.
3. Select **Upload My Add-in** (or **Manage My Add-ins** -> **Upload My Add-in**).
4. Browse to the `adapters/officejs/manifest.xml` file, and select **Upload**.
5. The SAB Task Pane icon will appear in the home ribbon, and clicking it will open the builder panel.

#### Sideloading in Excel on Windows/macOS:
* Follow Microsoft's official guide to place the `manifest.xml` file in a shared network folder (Windows) or the local add-in folder (`~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/` on macOS).
