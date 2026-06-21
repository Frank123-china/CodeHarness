import pytest
from pydantic import BaseModel, Field

from codeharness.tools import BaseTool, ToolRegistry, ToolResult
from codeharness.workspace import Workspace


class EchoArgs(BaseModel):
    message: str = Field(min_length=1)


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo a message."
    args_model = EchoArgs

    def execute(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        parsed = EchoArgs.model_validate(args)
        return ToolResult.ok(parsed.message, metadata={"root": str(workspace.root)})


def test_tool_can_register_query_and_execute(tmp_path) -> None:
    registry = ToolRegistry(Workspace(tmp_path))
    tool = EchoTool()

    registry.register(tool)
    result = registry.execute("echo", {"message": "hello"})

    assert registry.get("echo") is tool
    assert registry.names() == ["echo"]
    assert result.success is True
    assert result.output == "hello"


def test_duplicate_registration_fails(tmp_path) -> None:
    registry = ToolRegistry(Workspace(tmp_path))
    registry.register(EchoTool())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(EchoTool())


def test_unknown_tool_returns_structured_error(tmp_path) -> None:
    registry = ToolRegistry(Workspace(tmp_path))

    result = registry.execute("missing", {})

    assert result.success is False
    assert result.output is None
    assert "Unknown tool" in result.error


def test_invalid_parameters_return_structured_error(tmp_path) -> None:
    registry = ToolRegistry(Workspace(tmp_path))
    registry.register(EchoTool())

    result = registry.execute("echo", {"message": ""})

    assert result.success is False
    assert "Invalid parameters" in result.error
