import io
import os
import subprocess
import tempfile
from typing import Any, Literal, cast

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from adapters.uno.renderer import UNOAdapter
from core.ai.translator import describe_provider_setup, resolve_provider_api_key
from core.blueprint import Blueprint
from core.pipeline import run as run_pipeline
from core.scanner.context_builder import SpreadsheetContext
from renderers.xlsx_writer import XlsxRenderer

load_dotenv()

app = FastAPI(title="Spreadsheet App Builder API")

# Enable CORS for frontend task pane running on localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BuildRequest(BaseModel):
    prompt: str
    provider: Literal["claude", "gemini", "openai"] = os.getenv("SAB_AI_PROVIDER", "claude")  # type: ignore[assignment]
    model: str | None = None
    api_key: str | None = None
    context: dict[str, Any] | None = None


class RenderRequest(BaseModel):
    blueprint: dict[str, Any]


@app.get("/", response_class=HTMLResponse)
async def get_dashboard() -> HTMLResponse:
    """
    Serves the SAB Live Dashboard HTML front-end.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    static_file_path = os.path.join(current_dir, "static", "index.html")
    if not os.path.exists(static_file_path):
        raise HTTPException(status_code=404, detail="Dashboard index.html not found.")
    with open(static_file_path, encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.post("/api/build")
async def build(req: BuildRequest) -> dict[str, Any]:
    """
    Accepts prompt, queries AITranslator, validates, compiles, and returns the Blueprint JSON.
    """
    api_key = req.api_key
    if not api_key:
        if req.provider == "gemini":
            api_key = (
                os.getenv("SAB_GEMINI_API_KEY")
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("GOOGLE_API_KEY")
            )
        elif req.provider == "openai":
            api_key = os.getenv("SAB_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        else:
            api_key = os.getenv("SAB_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=f"No API key configured for provider {req.provider!r}."
        )

    # Parse incoming context if provided
    scanned_context = None
    if req.context:
        try:
            scanned_context = SpreadsheetContext.from_dict(req.context)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid context structure: {e}"
            )

    try:
        result = run_pipeline(
            prompt=req.prompt,
            api_key=api_key,
            provider=req.provider,
            model=req.model,
            validate_only=True,
            context=scanned_context,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Pipeline execution failed: {e}"
        )

    if not result.blueprint:
        raise HTTPException(
            status_code=500,
            detail="Pipeline failed to produce a valid blueprint."
        )

    return {"blueprint": result.blueprint.model_dump()}


@app.post("/api/render/xlsx")
async def render_xlsx(req: RenderRequest) -> StreamingResponse:
    """
    Accepts a blueprint, compiles it, and returns the binary XLSX workbook bytes.
    """
    try:
        from core.validator.schema import BlueprintValidator
        validator = BlueprintValidator()
        blueprint = validator.validate_blueprint(
            Blueprint.model_validate(req.blueprint)
        )
        renderer = XlsxRenderer()
        xlsx_bytes = renderer.render(blueprint)
        if not xlsx_bytes:
            raise HTTPException(status_code=500, detail="XLSX rendering failed to produce bytes.")

        headers = {
            "Content-Disposition": f"attachment; filename=\"{blueprint.meta.title or 'spreadsheet'}.xlsx\""
        }
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"XLSX rendering failed: {e}")


@app.post("/api/render/uno")
async def render_uno(req: RenderRequest) -> dict[str, str]:
    """
    Accepts a blueprint, connects to a running LibreOffice socket on port 2002, and renders.
    """
    try:
        from core.validator.schema import BlueprintValidator
        validator = BlueprintValidator()
        blueprint = validator.validate_blueprint(
            Blueprint.model_validate(req.blueprint)
        )
        from cli.sab import connect_uno
        doc = connect_uno(2002)

        renderer = UNOAdapter()
        renderer.render(blueprint, doc)
        return {"status": "success", "message": "Successfully rendered to LibreOffice Calc."}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"UNO render stage failed. Make sure LibreOffice is running on port 2002: {e}"
        )


@app.post("/api/render/onlyoffice")
async def render_onlyoffice(req: RenderRequest) -> dict[str, str]:
    """
    Accepts a blueprint, renders it to a temp XLSX file, and launches ONLYOFFICE in the background.
    """
    try:
        from core.validator.schema import BlueprintValidator
        validator = BlueprintValidator()
        blueprint = validator.validate_blueprint(
            Blueprint.model_validate(req.blueprint)
        )
        renderer = XlsxRenderer()
        xlsx_bytes = renderer.render(blueprint)
        if not xlsx_bytes:
            raise HTTPException(status_code=500, detail="XLSX rendering failed.")

        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(xlsx_bytes)

        # Launch ONLYOFFICE in background
        subprocess.Popen(
            ["onlyoffice-desktopeditors", temp_path],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {"status": "success", "message": f"Successfully opened in ONLYOFFICE. File: {temp_path}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ONLYOFFICE launch failed: {e}")


def start() -> None:
    provider_str = os.getenv("SAB_AI_PROVIDER", "claude")
    provider = cast(Literal["claude", "gemini", "openai"], provider_str)
    api_key, _ = resolve_provider_api_key(provider)
    print(describe_provider_setup(provider, api_key))
    uvicorn.run("cli.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
