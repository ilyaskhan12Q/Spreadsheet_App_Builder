import os
from typing import Any, Literal, cast

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.ai.translator import describe_provider_setup, resolve_provider_api_key
from core.pipeline import run as run_pipeline

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

    try:
        result = run_pipeline(
            prompt=req.prompt,
            api_key=api_key,
            provider=req.provider,
            model=req.model,
            validate_only=True,
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


def start() -> None:
    provider_str = os.getenv("SAB_AI_PROVIDER", "claude")
    provider = cast(Literal["claude", "gemini", "openai"], provider_str)
    api_key, _ = resolve_provider_api_key(provider)
    print(describe_provider_setup(provider, api_key))
    uvicorn.run("cli.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
