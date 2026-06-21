from codeharness.tools import create_default_registry
from codeharness.workspace import Workspace


def _names(registry):
    return [tool.name for tool in registry.list_tools()]


def test_default_registry_only_exposes_read_only_tools(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path))

    assert _names(registry) == ["list_files", "read_file"]
    assert [schema["name"] for schema in registry.schemas()] == ["list_files", "read_file"]


def test_allow_write_exposes_write_file(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path), allow_write=True)

    assert _names(registry) == ["list_files", "read_file", "write_file"]


def test_allow_command_exposes_run_command(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path), allow_command=True)

    assert _names(registry) == ["list_files", "read_file", "run_command"]


def test_unallowed_tool_is_rejected_at_execution_layer(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("write_file", {"path": "hello.txt", "content": "hello"})

    assert result.success is False
    assert "not allowed" in result.error
    assert result.metadata["not_allowed"] is True


def test_prompt_filter_and_execution_gate_are_independent(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path), allow_write=True)

    schema_names = [schema["name"] for schema in registry.schemas()]
    result = registry.execute("run_command", {"command": ["python", "--version"], "cwd": "."})

    assert "run_command" not in schema_names
    assert result.success is False
    assert "not allowed" in result.error


def test_full_permission_registry_keeps_all_tools_available(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path), allow_all=True)

    assert _names(registry) == ["list_files", "read_file", "run_command", "write_file"]
