import os
import sys
import json
import click
import logging
from typing import Optional
from dotenv import load_dotenv

from core.scanner.context_builder import ContextScanner
from core.ai.translator import AITranslator, describe_provider_setup
from core.validator.schema import BlueprintValidator

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sab.cli")


def connect_uno(port: int):
    """
    Establishes connection to a running LibreOffice instance via UNO socket.
    """
    try:
        import uno  # type: ignore
    except ImportError:
        click.echo("Error: Python 'uno' module not found. Please install python3-uno package.", err=True)
        sys.exit(1)

    try:
        local_context = uno.getComponentContext()
        resolver = local_context.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local_context
        )
        ctx = resolver.resolve(f"uno:socket,host=localhost,port={port};urp;StarOffice.ComponentContext")
        smgr = ctx.ServiceManager
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = desktop.getCurrentComponent()
        if not doc:
            click.echo("Error: Connected to LibreOffice, but no active document was found.", err=True)
            sys.exit(1)
        return doc
    except Exception as e:
        click.echo(f"Error connecting to LibreOffice on port {port}: {e}", err=True)
        click.echo("Please start LibreOffice with socket listening active: ", err=True)
        click.echo(f"libreoffice --calc --accept=\"socket,host=localhost,port={port};urp;StarOffice.ComponentContext\"", err=True)
        sys.exit(1)


@click.group()
def cli():
    """Spreadsheet App Builder (SAB) open-source engine CLI."""
    pass


@cli.command()
@click.argument("prompt")
@click.option("--adapter", type=click.Choice(["uno", "officejs"]), default="uno", show_default=True, help="The renderer adapter to use.")
@click.option("--provider", type=click.Choice(["claude", "gemini"]), default=os.getenv("SAB_AI_PROVIDER", "claude"), show_default=True, help="The AI provider to use.")
@click.option("--api-key", help="Override the provider API key.")
@click.option("--model", help="Override the provider model.")
@click.option("--validate-only", is_flag=True, help="Validate and output the generated blueprint JSON only, skip rendering.")
@click.option("--port", type=int, default=2002, help="The port LibreOffice Calc socket is listening on.")
def build(prompt: str, adapter: str, provider: str, api_key: Optional[str], model: Optional[str], validate_only: bool, port: int):
    """Generates and renders a spreadsheet application from a text PROMPT."""
    # 1. Scanning
    click.echo("Scanning context...")
    scanner = ContextScanner()
    # Create an empty/fresh context for new builds
    context = scanner.build_context()

    # 2. Translating
    click.echo(describe_provider_setup(provider, api_key))
    click.echo(f"Translating prompt using {provider.title()}...")
    translator = AITranslator(api_key=api_key, provider=provider, model=model)
    try:
        raw_blueprint_json = translator.translate(prompt, context)
    except Exception as e:
        click.echo(f"Translation failed: {e}", err=True)
        sys.exit(1)

    # 3. Validating
    click.echo("Validating blueprint...")
    validator = BlueprintValidator()
    try:
        blueprint = validator.validate(raw_blueprint_json)
    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        sys.exit(1)

    # 4. Handle Output
    if validate_only:
        click.echo("\n--- Blueprint JSON ---")
        click.echo(json.dumps(blueprint.model_dump(), indent=2))
        sys.exit(0)

    # 5. Rendering
    if adapter == "uno":
        click.echo(f"Connecting to LibreOffice Calc on port {port}...")
        doc = connect_uno(port)
        
        click.echo("Rendering blueprint using UNO adapter...")
        from adapters.uno.renderer import UNOAdapter
        uno_adapter = UNOAdapter()
        try:
            uno_adapter.render(blueprint, doc)
            click.echo("Successfully rendered application!")
        except Exception as e:
            click.echo(f"Rendering failed: {e}", err=True)
            sys.exit(1)
            
    elif adapter == "officejs":
        click.echo("Note: The Office.js adapter rendering is run from the React Task Pane UI.")
        click.echo("The compiled blueprint is printed below for manual loading if needed:")
        click.echo(json.dumps(blueprint.model_dump(), indent=2))


if __name__ == "__main__":
    cli()
