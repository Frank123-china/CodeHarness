import pytest
import sys

from codeharness.agent import AgentAction, AgentContext, AgentLoop, ScriptedActionProvider
from codeharness.tools import ToolResult, create_default_registry
from codeharness.workspace import Workspace


def _registry(tmp_path):
    return create_default_registry(Workspace(tmp_path))


def test_agent_loop_executes_tools_and_finishes(tmp_path) -> None:
    provider = ScriptedActionProvider(
        [
            AgentAction(
                type="tool",
                tool_name="write_file",
                arguments={"path": "hello.txt", "content": "hello"},
            ),
            AgentAction(type="tool", tool_name="read_file", arguments={"path": "hello.txt"}),
            AgentAction(type="finish", summary="Created and read hello.txt."),
        ]
    )
    loop = AgentLoop(_registry(tmp_path), provider, max_steps=5)

    result = loop.run("create and read a file")

    assert result.status == "completed"
    assert result.summary == "Created and read hello.txt."
    assert result.stop_reason == "finish"
    assert len(result.steps) == 3
    assert result.steps[0].tool_result.success is True
    assert result.steps[1].tool_result.output == "hello"
    assert result.steps[2].tool_result is None
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hello"


def test_agent_loop_runs_written_python_file(tmp_path) -> None:
    provider = ScriptedActionProvider(
        [
            AgentAction(
                type="tool",
                tool_name="write_file",
                arguments={"path": "hello.py", "content": "print('Hello, CodeHarness')\n"},
            ),
            AgentAction(
                type="tool",
                tool_name="run_command",
                arguments={"command": [sys.executable, "hello.py"], "cwd": "."},
            ),
            AgentAction(type="finish", summary="Python file executed."),
        ]
    )
    loop = AgentLoop(_registry(tmp_path), provider, max_steps=5)

    result = loop.run("create and run hello.py")

    assert result.status == "completed"
    assert (tmp_path / "hello.py").read_text(encoding="utf-8") == "print('Hello, CodeHarness')\n"
    command_result = result.steps[1].tool_result
    assert command_result.success is True
    assert command_result.output["exit_code"] == 0
    assert command_result.output["stdout"] == "Hello, CodeHarness\n"
    assert result.summary == "Python file executed."


def test_scripted_action_provider_returns_actions_in_order() -> None:
    provider = ScriptedActionProvider(
        [
            {"type": "tool", "tool_name": "list_files", "arguments": {"path": "."}},
            {"type": "finish", "summary": "done"},
        ]
    )
    context = AgentContext(task="list files", current_step=0)

    first = provider.next_action(context)
    second = provider.next_action(context)
    third = provider.next_action(context)

    assert first.type == "tool"
    assert first.tool_name == "list_files"
    assert second.type == "finish"
    assert second.summary == "done"
    assert third.type == "finish"
    assert third.summary == "No scripted actions remaining."


def test_agent_run_result_records_all_steps(tmp_path) -> None:
    provider = ScriptedActionProvider(
        [
            AgentAction(type="tool", tool_name="list_files", arguments={"path": "."}),
            AgentAction(type="finish", summary="listed"),
        ]
    )
    loop = AgentLoop(_registry(tmp_path), provider)

    result = loop.run("list files")

    assert [step.step_number for step in result.steps] == [1, 2]
    assert result.steps[0].action.tool_name == "list_files"
    assert result.steps[0].tool_result.success is True
    assert result.steps[1].action.type == "finish"


def test_unknown_tool_is_recorded_as_observation(tmp_path) -> None:
    provider = ScriptedActionProvider(
        [
            AgentAction(type="tool", tool_name="missing_tool", arguments={}),
            AgentAction(type="finish", summary="finished after missing tool"),
        ]
    )
    loop = AgentLoop(_registry(tmp_path), provider)

    result = loop.run("call missing tool")

    assert result.status == "completed"
    assert result.steps[0].tool_result.success is False
    assert "Unknown tool" in result.steps[0].tool_result.error
    assert result.steps[0].error == result.steps[0].tool_result.error


def test_tool_parameter_error_is_recorded(tmp_path) -> None:
    provider = ScriptedActionProvider(
        [
            AgentAction(type="tool", tool_name="read_file", arguments={}),
            AgentAction(type="finish", summary="finished after bad args"),
        ]
    )
    loop = AgentLoop(_registry(tmp_path), provider)

    result = loop.run("read with bad args")

    assert result.status == "completed"
    assert result.steps[0].tool_result.success is False
    assert "Invalid parameters" in result.steps[0].tool_result.error


def test_tool_execution_failure_does_not_crash_loop(tmp_path) -> None:
    provider = ScriptedActionProvider(
        [
            AgentAction(type="tool", tool_name="read_file", arguments={"path": "missing.txt"}),
            AgentAction(type="finish", summary="finished after failed read"),
        ]
    )
    loop = AgentLoop(_registry(tmp_path), provider)

    result = loop.run("read missing file")

    assert result.status == "completed"
    assert result.steps[0].tool_result.success is False
    assert "not found" in result.steps[0].tool_result.error
    assert result.summary == "finished after failed read"


def test_max_steps_exceeded(tmp_path) -> None:
    provider = ScriptedActionProvider(
        [
            AgentAction(type="tool", tool_name="list_files", arguments={"path": "."}),
            AgentAction(type="finish", summary="would finish"),
        ]
    )
    loop = AgentLoop(_registry(tmp_path), provider, max_steps=1)

    result = loop.run("list files")

    assert result.status == "max_steps_exceeded"
    assert result.stop_reason == "max_steps_exceeded"
    assert len(result.steps) == 1
    assert "Maximum steps exceeded" in result.error


def test_provider_exception_returns_failed_result(tmp_path) -> None:
    class BrokenProvider:
        def next_action(self, context: AgentContext) -> AgentAction:
            raise RuntimeError("provider failed")

    loop = AgentLoop(_registry(tmp_path), BrokenProvider())

    result = loop.run("use broken provider")

    assert result.status == "failed"
    assert result.stop_reason == "provider_error"
    assert result.error == "provider failed"


def test_empty_task_is_rejected(tmp_path) -> None:
    provider = ScriptedActionProvider([AgentAction(type="finish", summary="done")])
    loop = AgentLoop(_registry(tmp_path), provider)

    result = loop.run("   ")

    assert result.status == "failed"
    assert result.stop_reason == "empty_task"
    assert result.steps == []


def test_agent_loop_only_uses_registry_execute() -> None:
    class SpyRegistry:
        def __init__(self) -> None:
            self.calls = []

        def execute(self, name, args):
            self.calls.append((name, args))
            return ToolResult.ok("called registry")

    registry = SpyRegistry()
    provider = ScriptedActionProvider(
        [
            AgentAction(type="tool", tool_name="read_file", arguments={"path": "x.txt"}),
            AgentAction(type="finish", summary="done"),
        ]
    )
    loop = AgentLoop(registry, provider)

    result = loop.run("prove registry use")

    assert result.status == "completed"
    assert registry.calls == [("read_file", {"path": "x.txt"})]
    assert result.steps[0].tool_result.output == "called registry"


def test_agent_action_validates_required_fields() -> None:
    with pytest.raises(ValueError, match="tool_name"):
        AgentAction(type="tool")

    with pytest.raises(ValueError, match="summary"):
        AgentAction(type="finish")
