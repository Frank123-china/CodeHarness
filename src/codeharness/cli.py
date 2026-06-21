"""Command-line interface for CodeHarness."""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError

from codeharness.agent import AgentLoop, LLMActionProvider, PromptBuilder
from codeharness.config import CodeHarnessConfig, load_config
from codeharness.llm import LLMClientError, OpenAICompatibleClient
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
    typer.echo(f"LLM timeout: {config.llm_timeout}")
    typer.echo(f"API key configured: {'yes' if config.api_key_configured else 'no'}")
    if not config.api_key_configured:
        typer.echo("API key note: not configured; set CODEHARNESS_API_KEY to run the model-backed agent.")


@app.command()
def run(
    task: str = typer.Argument(..., help="Task description to pass to CodeHarness."),
    allow_write: bool = typer.Option(False, "--allow-write", help="Allow write_file."),
    allow_command: bool = typer.Option(False, "--allow-command", help="Allow run_command."),
) -> None:
    """Run the model-backed agent with explicit tool permissions."""

    config = _load_config_or_exit()
    registry = create_default_registry(
        Path.cwd(),
        command_timeout=config.command_timeout,
        allow_write=allow_write,
        allow_command=allow_command,
    )
    tool_names = registry.names_for_prompt()

    typer.echo(f"Task: {task}")
    typer.echo(f"Current working directory: {Path.cwd()}")
    typer.echo(f"Model: {config.model_name}")
    typer.echo(f"Allowed tools: {', '.join(tool_names)}")

    if not config.api_key_configured or config.api_key is None:
        typer.echo("API key is not configured. Set CODEHARNESS_API_KEY before running the model-backed agent.")
        raise typer.Exit(code=1)

    try:
        llm_client = OpenAICompatibleClient(
            model=config.model_name,
            api_key=config.api_key,
            base_url=config.base_url,
            timeout_seconds=config.llm_timeout,
        )
    except LLMClientError as exc:
        typer.echo(f"Failed to initialize LLM client: {exc}")
        raise typer.Exit(code=1) from exc

    provider = LLMActionProvider(llm_client, PromptBuilder(), registry)
    loop = AgentLoop(registry, provider, max_steps=config.max_steps)
    result = loop.run(task)
    _print_run_result(result)
    raise typer.Exit(code=0 if result.status == "completed" else 1)


@app.command("tools")
def list_tools(
    allow_write: bool = typer.Option(False, "--allow-write", help="Show write_file as an allowed tool."),
    allow_command: bool = typer.Option(False, "--allow-command", help="Show run_command as an allowed tool."),
) -> None:
    """List currently allowed development tools."""

    config = _load_config_or_exit()
    registry = create_default_registry(
        Path.cwd(),
        command_timeout=config.command_timeout,
        allow_write=allow_write,
        allow_command=allow_command,
    )
    for tool in registry.list_tools():
        typer.echo(f"{tool.name}: {tool.description}")


def _load_config_or_exit() -> CodeHarnessConfig:
    try:
        return load_config()
    except ValidationError as exc:
        typer.echo("Config loaded: no")
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc


def _print_run_result(result: Any) -> None:
    for step in result.steps:
        typer.echo(f"Step {step.step_number}: {step.action.type}")
        if step.action.type == "tool":
            typer.echo(f"  Tool: {step.action.tool_name}")
            tool_result = step.tool_result
            if tool_result is None:
                typer.echo("  Tool success: no result")
                continue
            typer.echo(f"  Tool success: {'yes' if tool_result.success else 'no'}")
            if tool_result.error:
                typer.echo(f"  Tool error: {_truncate(str(tool_result.error))}")
        elif step.action.summary:
            typer.echo(f"  Summary: {step.action.summary}")

    typer.echo(f"Status: {result.status}")
    if result.summary:
        typer.echo(f"Summary: {result.summary}")
    typer.echo(f"Stop reason: {result.stop_reason}")
    if result.error:
        typer.echo(f"Error: {_truncate(str(result.error))}")


def _truncate(value: str, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}... truncated"
