import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
from dotenv import load_dotenv

from core.scanner.context_builder import ContextScanner
from core.ai.translator import AITranslator, describe_provider_setup, resolve_provider_api_key
from core.validator.schema import BlueprintValidator

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
    provider: Literal["claude", "gemini"] = os.getenv("SAB_AI_PROVIDER", "claude")
    model: str | None = None
    api_key: str | None = None


@app.post("/api/build")
async def build(req: BuildRequest):
    """
    Accepts prompt, queries AITranslator, validates, and returns the Blueprint JSON.
    """
    api_key = req.api_key
    if not api_key:
        if req.provider == "gemini":
            api_key = os.getenv("SAB_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        else:
            api_key = os.getenv("SAB_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=f"No API key configured for provider {req.provider!r}."
        )

    # 1. Scanner Context
    scanner = ContextScanner()
    context = scanner.build_context()

    # 2. Translate Prompt to JSON Blueprint
    translator = AITranslator(api_key=api_key, provider=req.provider, model=req.model)
    try:
        raw_json = translator.translate(req.prompt, context)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Translation failed: {e}"
        )

    # 3. Validate Blueprint Constraints
    validator = BlueprintValidator()
    try:
        blueprint = validator.validate(raw_json)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Blueprint validation failed: {e}"
        )

    return {"blueprint": blueprint.model_dump()}


def start():
    provider = os.getenv("SAB_AI_PROVIDER", "claude")
    api_key, _ = resolve_provider_api_key(provider)
    print(describe_provider_setup(provider, api_key))
    uvicorn.run("cli.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
