"""Minimal tool interface."""

from __future__ import annotations

from pydantic import BaseModel

from codeharness.tools.result import ToolResult
from codeharness.workspace import Workspace


class BaseTool:
    """Base interface for tools executed through the registry."""

    name: str
    description: str
    args_model: type[BaseModel]

    def validate_args(self, args: object) -> BaseModel:
        """Validate raw tool arguments with the tool's Pydantic model."""

        return self.args_model.model_validate(args)

    def execute(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        """Execute the tool against a workspace."""

        raise NotImplementedError("Tool execution is not implemented yet.")
