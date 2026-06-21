"""Command-line interface for CodeHarness."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

import typer
from pydantic import ValidationError

from codeharness.config import CodeHarnessConfig, load_config
from codeharness.tools import create_default_registry

app = typer.Typer(
    help="CodeHarness is a lightweight CLI scaffold for a future programming agent.",
    no_args_is_help=True,
)


@app.command()
def doctor() -> None:
    """Check the local CodeHarness runtime environment."""

    config = _load_config_or_exit()
    typer.echo(f"Python version: {platform.python_version()}")
    typer.echo(f"Python executable: {sys.executable}")
    typer.echo(f"Current working directory: {Path.cwd()}")
    typer.echo("Config loaded: yes")
    typer.echo(f"Model: {config.model_name}")
    typer.echo(f"Base URL: {config.base_url}")
    typer.echo(f"Max steps: {config.max_steps}")
    typer.echo(f"Command timeout: {config.command_timeout}")
    typer.echo(f"API key configured: {'yes' if config.api_key_configured else 'no'}")
    if not config.api_key_configured:
        typer.echo("API key note: not configured; this is okay for the scaffold stage.")


@app.command()
def run(task: str = typer.Argument(..., help="Task description to pass to CodeHarness.")) -> None:
    """Accept a task for the placeholder agent runtime."""

    config = _load_config_or_exit()
    typer.echo(f"Received task: {task}")
    typer.echo(f"Current working directory: {Path.cwd()}")
    typer.echo(f"Model: {config.model_name}")
    typer.echo("LLM 驱动的 Agent Runtime 尚未接入")


@app.command("tools")
def list_tools() -> None:
    """List currently registered development tools."""

    config = _load_config_or_exit()
    registry = create_default_registry(Path.cwd(), command_timeout=config.command_timeout)
    for tool in registry.list_tools():
        typer.echo(f"{tool.name}: {tool.description}")


def _load_config_or_exit() -> CodeHarnessConfig:
    try:
        return load_config()
    except ValidationError as exc:
        typer.echo("Config loaded: no")
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
