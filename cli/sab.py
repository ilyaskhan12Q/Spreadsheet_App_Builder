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
        else:
            click.echo("Successfully rendered application!")


if __name__ == "__main__":
    cli()
