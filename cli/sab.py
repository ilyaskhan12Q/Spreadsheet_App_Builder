import json
import logging
import os
import sys
from typing import Any, Literal, cast

import click
from dotenv import load_dotenv

from core.ai.translator import describe_provider_setup
from core.pipeline import run as run_pipeline

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sab.cli")


def connect_uno(port: int) -> Any:
    """
    Establishes connection to a running LibreOffice instance via UNO socket.
    """
    try:
        import uno  # type: ignore
    except ImportError:
        click.echo(
            "Error: Python 'uno' module not found. Please install python3-uno package.",
            err=True
        )
        sys.exit(1)

    try:
        local_context = uno.getComponentContext()
        resolver = local_context.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local_context
        )
        ctx = resolver.resolve(
            f"uno:socket,host=localhost,port={port};urp;StarOffice.ComponentContext"
        )
        smgr = ctx.ServiceManager
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = desktop.getCurrentComponent()
        if not doc:
            click.echo(
                "Error: Connected to LibreOffice, but no active document was found.",
                err=True
            )
            sys.exit(1)
        return doc
    except Exception as e:
        click.echo(f"Error connecting to LibreOffice on port {port}: {e}", err=True)
        click.echo("Please start LibreOffice with socket listening active: ", err=True)
        click.echo(
            f"libreoffice --calc --accept=\"socket,host=localhost,port={port};"
            "urp;StarOffice.ComponentContext\"",
            err=True
        )
        sys.exit(1)


@click.group()
def cli() -> None:
    """Spreadsheet App Builder (SAB) open-source engine CLI."""
    pass


@cli.command()
@click.argument("prompt")
@click.option(
    "--adapter",
    type=click.Choice(["xlsx", "uno", "officejs"]),
    default="xlsx",
    show_default=True,
    help="The renderer adapter to use."
)
@click.option(
    "--provider",
    type=click.Choice(["claude", "gemini", "openai"]),
    default=os.getenv("SAB_AI_PROVIDER", "claude"),
    show_default=True,
    help="The AI provider to use."
)
@click.option("--api-key", help="Override the provider API key.")
@click.option("--model", help="Override the provider model.")
@click.option(
    "--validate-only",
    is_flag=True,
    help="Validate and output the generated blueprint JSON only, skip rendering."
)
@click.option(
    "--port",
    type=int,
    default=2002,
    help="The port LibreOffice Calc socket is listening on."
)
@click.option(
    "--output",
    "-o",
    default="output.xlsx",
    help="The output filepath for the xlsx adapter."
)
def build(
    prompt: str,
    adapter: str,
    provider: str,
    api_key: str | None,
    model: str | None,
    validate_only: bool,
    port: int,
    output: str,
) -> None:
    """Generates and renders a spreadsheet application from a text PROMPT."""
    # Resolve API Key
    resolved_provider = cast(Literal["claude", "gemini", "openai"], provider)
    if not api_key:
        if resolved_provider == "gemini":
            api_key = (
                os.getenv("SAB_GEMINI_API_KEY")
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("GOOGLE_API_KEY")
            )
        elif resolved_provider == "openai":
            api_key = os.getenv("SAB_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        else:
            api_key = os.getenv("SAB_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        click.echo(
            f"Error: No API key found for provider {resolved_provider}.",
            err=True
        )
        sys.exit(1)

    # 1. Connected document or output path
    handle: Any = None
    if not validate_only:
        if adapter == "uno":
            click.echo(f"Connecting to LibreOffice Calc on port {port}...")
            handle = connect_uno(port)
        elif adapter == "xlsx":
            handle = output

    # 2. Setup message
    click.echo(describe_provider_setup(resolved_provider, api_key))
    click.echo(f"Running pipeline using {resolved_provider.title()}...")

    # 3. Execute Pipeline
    try:
        result = run_pipeline(
            prompt=prompt,
            api_key=api_key,
            provider=resolved_provider,
            model=model,
            adapter_name=adapter,
            spreadsheet_handle=handle,
            validate_only=validate_only,
        )
    except Exception as e:
        click.echo(f"Pipeline failed: {e}", err=True)
        sys.exit(1)

    # 4. Output / Print results
    if result.blueprint:
        if validate_only:
            click.echo("\n--- Blueprint JSON ---")
            click.echo(json.dumps(result.blueprint.model_dump(), indent=2))
        elif adapter == "officejs":
            click.echo(
                "Note: The Office.js adapter rendering is run from the React Task Pane UI."
            )
            click.echo("The compiled blueprint is printed below:")
            click.echo(json.dumps(result.blueprint.model_dump(), indent=2))
            click.echo("Successfully rendered application!")


@cli.command()
@click.option(
    "--adapter",
    type=click.Choice(["xlsx", "uno", "officejs"]),
    default="xlsx",
    show_default=True,
    help="The renderer adapter to use."
)
@click.option(
    "--provider",
    type=click.Choice(["claude", "gemini", "openai"]),
    default=os.getenv("SAB_AI_PROVIDER", "claude"),
    show_default=True,
    help="The AI provider to use."
)
@click.option("--api-key", help="Override the provider API key.")
@click.option("--model", help="Override the provider model.")
@click.option(
    "--output",
    "-o",
    default="output.xlsx",
    help="The output filepath for the xlsx adapter."
)
def wizard(
    adapter: str,
    provider: str,
    api_key: str | None,
    model: str | None,
    output: str,
) -> None:
    """Interactive wizard to guide you in setting up and styling your spreadsheet application."""
    click.echo("================================================================")
    click.echo("  Spreadsheet App Builder (SAB) - Interactive Setup Wizard")
    click.echo("================================================================")

    # 1. Ask about the app requirements
    prompt = click.prompt("\nWhat application do you want to build?")

    # 2. Ask about visual styling preferences
    click.echo("\n--- Visual Styling & Preferences ---")
    palette = click.prompt(
        "Choose a color palette",
        type=click.Choice(["ocean", "sunset", "forest", "corporate", "monochrome"]),
        default="corporate"
    )

    font = click.prompt(
        "Choose a font style",
        type=click.Choice(["modern", "classic", "monospace"]),
        default="modern"
    )

    emoji_enabled = click.confirm(
        "Enable emoji decorations in headers/labels?",
        default=True
    )

    style_preset = click.prompt(
        "Choose a layout style preset",
        type=click.Choice(["minimal", "bold", "professional", "playful"]),
        default="professional"
    )

    # Resolve API Key
    resolved_provider = cast(Literal["claude", "gemini", "openai"], provider)
    if not api_key:
        if resolved_provider == "gemini":
            api_key = (
                os.getenv("SAB_GEMINI_API_KEY")
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("GOOGLE_API_KEY")
            )
        elif resolved_provider == "openai":
            api_key = os.getenv("SAB_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        else:
            api_key = os.getenv("SAB_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        click.echo(
            f"Error: No API key found for provider {resolved_provider}.",
            err=True
        )
        sys.exit(1)

    # Output path
    handle: Any = None
    if adapter == "uno":
        click.echo("\nConnecting to LibreOffice Calc on port 2002...")
        handle = connect_uno(2002)
    elif adapter == "xlsx":
        handle = output

    click.echo("\nRunning AI translation engine...")

    from core.ai.translator import AITranslator
    from core.app_spec import AppSpec, DesignPreferences
    from core.compiler.app_spec_to_blueprint import compile_app_spec
    from core.scanner.context_builder import ContextScanner
    from core.validator.schema import BlueprintValidator

    # Stage 1: Context Scanner
    scanner = ContextScanner()
    context = scanner.build_context(handle)

    # Stage 2: Translate
    translator = AITranslator(api_key=api_key, provider=resolved_provider, model=model)
    try:
        raw_json = translator.translate(prompt, context)
        app_spec = AppSpec.model_validate_json(raw_json)
    except Exception as exc:
        click.echo(f"Pipeline failed during translation: {exc}", err=True)
        sys.exit(1)

    # Overwrite design block with user choices from the wizard
    app_spec.design = DesignPreferences(
        palette=palette,
        font=font,
        emoji_enabled=emoji_enabled,
        style_preset=style_preset
    )

    # Stage 3: Compile and Validate
    click.echo("Compiling and validating app blueprint...")
    try:
        compiled_blueprint = compile_app_spec(app_spec)
        validator = BlueprintValidator()
        blueprint = validator.validate_blueprint(compiled_blueprint)
    except Exception as exc:
        click.echo(f"Pipeline failed during compilation/validation: {exc}", err=True)
        sys.exit(1)

    # Stage 4: Render
    click.echo(f"Rendering application to {output} using adapter {adapter}...")
    if adapter == "uno":
        from adapters.uno.renderer import UNOAdapter
        try:
            UNOAdapter().render(blueprint, handle)
        except Exception as exc:
            click.echo(f"UNO render stage failed: {exc}", err=True)
            sys.exit(1)
    elif adapter == "xlsx":
        from renderers.xlsx_writer import XlsxRenderer
        try:
            XlsxRenderer().render(blueprint, save_path=output)
        except Exception as exc:
            click.echo(f"XLSX render stage failed: {exc}", err=True)
            sys.exit(1)

    click.echo(f"\nSuccess! Your customized spreadsheet app has been generated and saved to {output}.")


if __name__ == "__main__":
    cli()

