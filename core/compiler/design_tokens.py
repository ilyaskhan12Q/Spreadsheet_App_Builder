"""
core/compiler/design_tokens.py — Design token resolver.

Resolves user DesignPreferences (palette name, font hint, style preset)
into concrete hex colors, font names, sizes, and styling rules that the
region templates consume. Provides sensible defaults per app_type when
the user doesn't specify preferences.

No AI involvement — this is pure deterministic mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.app_spec import AppType, DesignPreferences


# ---------------------------------------------------------------------------
# Palette definitions — role-based hex colors
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Palette:
    """A complete color palette with role-based hex values."""

    name: str
    primary: str
    primary_text: str
    secondary: str
    secondary_text: str
    input_bg: str
    label_bg: str
    border: str
    success: str
    warning: str
    danger: str


PALETTES: dict[str, Palette] = {
    "ocean": Palette(
        name="ocean",
        primary="#1565C0",
        primary_text="#FFFFFF",
        secondary="#E3F2FD",
        secondary_text="#0D47A1",
        input_bg="#FAFAFA",
        label_bg="#E8EAF6",
        border="#90CAF9",
        success="#2E7D32",
        warning="#F9A825",
        danger="#C62828",
    ),
    "sunset": Palette(
        name="sunset",
        primary="#E65100",
        primary_text="#FFFFFF",
        secondary="#FFF3E0",
        secondary_text="#BF360C",
        input_bg="#FFFDE7",
        label_bg="#FBE9E7",
        border="#FFAB91",
        success="#2E7D32",
        warning="#FF8F00",
        danger="#B71C1C",
    ),
    "forest": Palette(
        name="forest",
        primary="#2E7D32",
        primary_text="#FFFFFF",
        secondary="#E8F5E9",
        secondary_text="#1B5E20",
        input_bg="#FAFAFA",
        label_bg="#F1F8E9",
        border="#A5D6A7",
        success="#1B5E20",
        warning="#F57F17",
        danger="#C62828",
    ),
    "corporate": Palette(
        name="corporate",
        primary="#1A237E",
        primary_text="#FFFFFF",
        secondary="#E8EAF6",
        secondary_text="#283593",
        input_bg="#FAFAFA",
        label_bg="#F5F5F5",
        border="#BDBDBD",
        success="#2E7D32",
        warning="#FF8F00",
        danger="#C62828",
    ),
    "monochrome": Palette(
        name="monochrome",
        primary="#212121",
        primary_text="#FFFFFF",
        secondary="#F5F5F5",
        secondary_text="#424242",
        input_bg="#FFFFFF",
        label_bg="#EEEEEE",
        border="#9E9E9E",
        success="#388E3C",
        warning="#FFA000",
        danger="#D32F2F",
    ),
}

# ---------------------------------------------------------------------------
# Font presets
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FontPreset:
    """Font family and base size."""

    name: str
    family: str
    base_size: float
    header_size: float
    title_size: float


FONTS: dict[str, FontPreset] = {
    "modern": FontPreset(
        name="modern",
        family="Calibri",
        base_size=11.0,
        header_size=12.0,
        title_size=16.0,
    ),
    "classic": FontPreset(
        name="classic",
        family="Times New Roman",
        base_size=11.0,
        header_size=12.0,
        title_size=16.0,
    ),
    "monospace": FontPreset(
        name="monospace",
        family="Consolas",
        base_size=10.0,
        header_size=11.0,
        title_size=14.0,
    ),
}

# ---------------------------------------------------------------------------
# Style presets — affect borders, emphasis, spacing
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StylePreset:
    """Styling rules that affect borders, fills, and emphasis."""

    name: str
    header_border: str  # BorderStyle value
    cell_border: str
    use_section_fills: bool
    use_alternating_rows: bool
    row_height_base: float
    row_height_header: float
    row_height_title: float
    col_width_label: float
    col_width_data: float


STYLE_PRESETS: dict[str, StylePreset] = {
    "minimal": StylePreset(
        name="minimal",
        header_border="thin",
        cell_border="none",
        use_section_fills=False,
        use_alternating_rows=False,
        row_height_base=18.0,
        row_height_header=22.0,
        row_height_title=28.0,
        col_width_label=15.0,
        col_width_data=18.0,
    ),
    "bold": StylePreset(
        name="bold",
        header_border="medium",
        cell_border="thin",
        use_section_fills=True,
        use_alternating_rows=True,
        row_height_base=20.0,
        row_height_header=25.0,
        row_height_title=32.0,
        col_width_label=18.0,
        col_width_data=20.0,
    ),
    "professional": StylePreset(
        name="professional",
        header_border="thin",
        cell_border="thin",
        use_section_fills=True,
        use_alternating_rows=False,
        row_height_base=20.0,
        row_height_header=24.0,
        row_height_title=30.0,
        col_width_label=16.0,
        col_width_data=20.0,
    ),
    "playful": StylePreset(
        name="playful",
        header_border="medium",
        cell_border="dashed",
        use_section_fills=True,
        use_alternating_rows=True,
        row_height_base=22.0,
        row_height_header=26.0,
        row_height_title=34.0,
        col_width_label=18.0,
        col_width_data=22.0,
    ),
}

# ---------------------------------------------------------------------------
# Auto-defaults per app_type
# ---------------------------------------------------------------------------

APP_TYPE_DEFAULTS: dict[str, dict[str, str]] = {
    "pos": {"palette": "ocean", "font": "modern", "style_preset": "bold"},
    "dashboard": {"palette": "sunset", "font": "modern", "style_preset": "minimal"},
    "invoice": {"palette": "corporate", "font": "classic", "style_preset": "professional"},
    "tracker": {"palette": "forest", "font": "modern", "style_preset": "professional"},
    "other": {"palette": "monochrome", "font": "modern", "style_preset": "professional"},
}

# ---------------------------------------------------------------------------
# Emoji maps
# ---------------------------------------------------------------------------

SECTION_EMOJI: dict[str, str] = {
    "header": "📋",
    "input_form": "✏️",
    "data_table": "📊",
    "summary": "💰",
    "actions": "⚡",
    "kpi_row": "📈",
}

APP_TYPE_EMOJI: dict[str, str] = {
    "pos": "🛒",
    "dashboard": "📊",
    "invoice": "🧾",
    "tracker": "📝",
    "other": "📄",
}

# ---------------------------------------------------------------------------
# Resolved tokens — the output of the resolver
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResolvedTokens:
    """Fully resolved design tokens ready for consumption by templates.

    All values are concrete (hex colors, font names, point sizes).
    """

    palette: Palette
    font: FontPreset
    style: StylePreset
    emoji_enabled: bool
    app_type_emoji: str
    section_emojis: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public resolver
# ---------------------------------------------------------------------------

def resolve_tokens(
    app_type: AppType,
    preferences: DesignPreferences | None = None,
) -> ResolvedTokens:
    """Resolve user DesignPreferences into concrete ResolvedTokens.

    Falls back to app_type defaults for any unspecified preference.

    Args:
        app_type: The app type to resolve defaults for.
        preferences: Optional user design preferences.

    Returns:
        Fully resolved tokens with concrete values.
    """
    prefs = preferences or DesignPreferences()
    defaults = APP_TYPE_DEFAULTS.get(app_type.value, APP_TYPE_DEFAULTS["other"])

    # Resolve palette
    palette_name = prefs.palette or defaults["palette"]
    palette = PALETTES.get(palette_name, PALETTES[defaults["palette"]])

    # Resolve font
    font_name = prefs.font or defaults["font"]
    font = FONTS.get(font_name, FONTS[defaults["font"]])

    # Resolve style preset
    preset_name = prefs.style_preset or defaults["style_preset"]
    style = STYLE_PRESETS.get(preset_name, STYLE_PRESETS[defaults["style_preset"]])

    # Resolve emojis
    emoji_enabled = prefs.emoji_enabled
    type_emoji = APP_TYPE_EMOJI.get(app_type.value, "📄") if emoji_enabled else ""
    section_emojis = dict(SECTION_EMOJI) if emoji_enabled else {}

    return ResolvedTokens(
        palette=palette,
        font=font,
        style=style,
        emoji_enabled=emoji_enabled,
        app_type_emoji=type_emoji,
        section_emojis=section_emojis,
    )


# ---------------------------------------------------------------------------
# Format hint resolver
# ---------------------------------------------------------------------------

FORMAT_HINT_MAP: dict[str, str] = {
    "currency": "$#,##0.00",
    "percentage": "0.00%",
    "integer": "0",
    "number": "0.00",
    "date": "yyyy-mm-dd",
    "text": "@",
}


def resolve_format_hint(hint: str | None) -> str | None:
    """Convert a semantic format hint to a spreadsheet number format string.

    Args:
        hint: Semantic format hint (e.g., 'currency', 'percentage').

    Returns:
        Number format string for the spreadsheet, or None if no hint.
    """
    if hint is None:
        return None
    return FORMAT_HINT_MAP.get(hint.lower())
