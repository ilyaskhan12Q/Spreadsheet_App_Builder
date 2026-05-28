"""
core/pipeline.py — Full orchestration pipeline for SAB.

Pipeline stages:
    1. ContextScanner   → SpreadsheetContext
    2. AITranslator     → raw JSON blueprint string
    3. BlueprintValidator → Blueprint (Pydantic model)
    4. Adapter.render()  → side-effects on the spreadsheet
"""

import logging
from typing import Any, Optional

from core.blueprint import Blueprint
from core.scanner.context_builder import ContextScanner, SpreadsheetContext
from core.ai.translator import AITranslator, TranslationError
from core.validator.schema import BlueprintValidator
from adapters.uno.renderer import UNOAdapter

logger = logging.getLogger("sab.pipeline")


class PipelineError(Exception):
    """Raised when any stage of the pipeline fails irrecoverably."""
    pass


class PipelineResult:
    """Carries the artefacts produced at each stage."""

    def __init__(self) -> None:
        self.context: Optional[SpreadsheetContext] = None
        self.raw_json: Optional[str] = None
        self.blueprint: Optional[Blueprint] = None
        self.rendered: bool = False

    def __repr__(self) -> str:
        title = self.blueprint.meta.title if self.blueprint else "<unresolved>"
        return f"PipelineResult(title={title!r}, rendered={self.rendered})"


def run(
    prompt: str,
    *,
    api_key: str,
    provider: str = "claude",
    model: Optional[str] = None,
    adapter_name: str = "uno",
    spreadsheet_handle: Any = None,
    validate_only: bool = False,
) -> PipelineResult:
    """
    Execute the full SAB pipeline end-to-end.

    Parameters
    ----------
    prompt : str
        Natural-language description of the spreadsheet app.
    api_key : str
        Provider API key.
    provider : {"claude", "gemini"}
        Which AI provider to use.
    model : str, optional
        Override the default model for the selected provider.
    adapter_name : {"uno", "officejs"}
        Which rendering adapter to use.
    spreadsheet_handle : Any, optional
        An open document object (UNO XComponent) passed to the renderer.
    validate_only : bool
        When True, stop after validation — don't render.

    Returns
    -------
    PipelineResult
    """
    result = PipelineResult()

    # ── Stage 1: Scan ──────────────────────────────────────────────────
    logger.info("Stage 1/4 — Scanning context")
    scanner = ContextScanner()
    result.context = scanner.build_context(spreadsheet_handle)

    # ── Stage 2: Translate ─────────────────────────────────────────────
    logger.info("Stage 2/4 — Translating prompt via AI")
    translator = AITranslator(api_key=api_key, provider=provider, model=model)
    try:
        result.raw_json = translator.translate(prompt, result.context)
    except TranslationError as exc:
        raise PipelineError(f"Translation stage failed: {exc}") from exc

    # ── Stage 3: Validate ──────────────────────────────────────────────
    logger.info("Stage 3/4 — Validating blueprint")
    validator = BlueprintValidator()
    try:
        result.blueprint = validator.validate(result.raw_json)
    except Exception as exc:
        raise PipelineError(f"Validation stage failed: {exc}") from exc

    if validate_only:
        logger.info("validate_only=True — skipping render stage")
        return result

    # ── Stage 4: Render ────────────────────────────────────────────────
    logger.info("Stage 4/4 — Rendering with adapter=%s", adapter_name)
    if adapter_name == "uno":
        adapter = UNOAdapter()
        try:
            adapter.render(result.blueprint, spreadsheet_handle)
            result.rendered = True
        except Exception as exc:
            raise PipelineError(f"UNO render stage failed: {exc}") from exc

    elif adapter_name == "officejs":
        # Office.js rendering happens client-side in the React task pane;
        # the Python pipeline simply returns the validated blueprint.
        logger.info("Office.js adapter — blueprint returned for client-side rendering")
        result.rendered = False

    else:
        raise PipelineError(f"Unknown adapter: {adapter_name!r}")

    return result
