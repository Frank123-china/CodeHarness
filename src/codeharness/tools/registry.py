"""Tool registry for validated tool execution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from codeharness.tools.base import BaseTool
from codeharness.tools.result import ToolResult
from codeharness.workspace import Workspace


class ToolRegistry:
    """Registers tools and executes them as the only runtime entry point."""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool definition."""

        if tool.name in self._tools:
            raise ValueError(f"Tool is already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Return a registered tool by name, if present."""

        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """Return registered tools sorted by name."""

        return [self._tools[name] for name in self.names()]

    def names(self) -> list[str]:
        """Return registered tool names in sorted order."""

        return sorted(self._tools)

    def execute(self, name: str, args: Mapping[str, Any] | None = None) -> ToolResult:
        """Validate parameters and execute a registered tool."""

        tool = self.get(name)
        if tool is None:
            return ToolResult.fail(f"Unknown tool: {name}", metadata={"tool": name})

        try:
            parsed_args = tool.validate_args(args or {})
        except ValidationError as exc:
            return ToolResult.fail(
                f"Invalid parameters for tool '{name}': {exc}",
                metadata={"tool": name},
            )

        try:
            return tool.execute(parsed_args, self.workspace)
        except Exception as exc:
            return ToolResult.fail(f"Tool '{name}' failed: {exc}", metadata={"tool": name})
