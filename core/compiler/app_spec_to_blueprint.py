"""
core/compiler/app_spec_to_blueprint.py — Deterministic compiler.

Translates an AppSpec semantic model into a complete, coordinate-resolved Blueprint.
Uses the DesignPreferences to resolve tokens, and invokes the appropriate template.
"""

from core.app_spec import AppSpec, AppType
from core.blueprint import AppType as BlueprintAppType
from core.blueprint import Blueprint
from core.compiler.design_tokens import resolve_tokens
from core.compiler.region_templates import dashboard, invoice, pos


class CompilationError(Exception):
    """Raised when compilation fails."""
    pass


def compile_app_spec(spec: AppSpec) -> Blueprint:
    """
    Compile a semantic AppSpec into a concrete Blueprint.
    """
    # 1. Resolve tokens
    tokens = resolve_tokens(spec.app_type, spec.design)

    # 2. Select appropriate template compiler
    if spec.app_type == AppType.POS:
        blueprint = pos.compile(spec, tokens)
    elif spec.app_type == AppType.DASHBOARD:
        blueprint = dashboard.compile(spec, tokens)
    elif spec.app_type == AppType.INVOICE:
        blueprint = invoice.compile(spec, tokens)
    elif spec.app_type == AppType.TRACKER:
        # Fallback to POS layout for tracker, but set meta.app_type to BlueprintAppType.OTHER
        blueprint = pos.compile(spec, tokens)
        blueprint.meta.app_type = BlueprintAppType.OTHER
    elif spec.app_type == AppType.OTHER:
        blueprint = pos.compile(spec, tokens)
        blueprint.meta.app_type = BlueprintAppType.OTHER
    else:
        raise CompilationError(f"Unsupported app type for compilation: {spec.app_type}")

    return blueprint
