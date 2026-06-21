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

    def __init__(self, workspace: Workspace, allowed_tools: set[str] | None = None) -> None:
        self.workspace = workspace
        self._allowed_tools = allowed_tools
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool definition."""

        if tool.name in self._tools:
            raise ValueError(f"Tool is already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Return a registered tool by name, if present."""

        if not self.is_allowed(name):
            return None
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """Return registered tools sorted by name."""

        return [self._tools[name] for name in self.names() if self.is_allowed(name)]

    def names(self) -> list[str]:
        """Return registered tool names in sorted order."""

        return sorted(self._tools)

    def names_for_prompt(self) -> list[str]:
        """Return allowed tool names in sorted order."""

        return [name for name in self.names() if self.is_allowed(name)]

    def schemas(self) -> list[dict[str, object]]:
        """Return JSON-serializable schemas for all registered tools."""

        return [self._tools[name].schema() for name in self.names() if self.is_allowed(name)]

    def is_allowed(self, name: str) -> bool:
        """Return whether a tool is currently allowed."""

        return self._allowed_tools is None or name in self._allowed_tools

    def execute(self, name: str, args: Mapping[str, Any] | None = None) -> ToolResult:
        """Validate parameters and execute a registered tool."""

        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.fail(f"Unknown tool: {name}", metadata={"tool": name})
        if not self.is_allowed(name):
            return ToolResult.fail(
                f"Tool is not allowed: {name}",
                metadata={"tool": name, "not_allowed": True},
            )

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
