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
) -> ToolRegistry:
    """Create a registry with the built-in workspace file tools."""

    active_workspace = workspace if isinstance(workspace, Workspace) else Workspace(workspace or Path.cwd())
    registry = ToolRegistry(active_workspace)
    registry.register(ListFilesTool())
    registry.register(ReadFileTool())
    registry.register(RunCommandTool(default_timeout_seconds=command_timeout or 30))
    registry.register(WriteFileTool())
    return registry
