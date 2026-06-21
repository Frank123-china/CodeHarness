"""Default tool registry construction."""

from __future__ import annotations

from pathlib import Path

from codeharness.tools.command import RunCommandTool
from codeharness.tools.files import ListFilesTool, ReadFileTool, WriteFileTool
from codeharness.tools.registry import ToolRegistry
from codeharness.workspace import Workspace


def create_default_registry(
    workspace: Workspace | str | Path | None = None,
    command_timeout: int | None = None,
    allow_write: bool = False,
    allow_command: bool = False,
    allow_all: bool = False,
) -> ToolRegistry:
    """Create a registry with the built-in workspace file tools."""

    active_workspace = workspace if isinstance(workspace, Workspace) else Workspace(workspace or Path.cwd())
    allowed_tools = None if allow_all else _allowed_tool_names(allow_write=allow_write, allow_command=allow_command)
    registry = ToolRegistry(active_workspace, allowed_tools=allowed_tools)
    registry.register(ListFilesTool())
    registry.register(ReadFileTool())
    registry.register(RunCommandTool(default_timeout_seconds=command_timeout or 30))
    registry.register(WriteFileTool())
    return registry


def _allowed_tool_names(allow_write: bool, allow_command: bool) -> set[str]:
    allowed = {"list_files", "read_file"}
    if allow_write:
        allowed.add("write_file")
    if allow_command:
        allowed.add("run_command")
    return allowed
