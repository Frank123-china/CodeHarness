import sys

from codeharness.safety import CommandPolicy
from codeharness.tools import create_default_registry
from codeharness.tools.command import MAX_COMMAND_OUTPUT_CHARS
from codeharness.workspace import Workspace


def _registry(tmp_path):
    return create_default_registry(Workspace(tmp_path), allow_command=True)


def test_run_command_executes_python_and_captures_stdout(tmp_path) -> None:
    result = _registry(tmp_path).execute(
        "run_command",
        {"command": [sys.executable, "-c", "print('hello')"], "cwd": "."},
    )

    assert result.success is True
    assert result.output["exit_code"] == 0
    assert result.output["stdout"] == "hello\n"
    assert result.output["stderr"] == ""
    assert result.output["timed_out"] is False


def test_run_command_captures_stderr(tmp_path) -> None:
    result = _registry(tmp_path).execute(
        "run_command",
        {
            "command": [
                sys.executable,
                "-c",
                "import sys; print('problem', file=sys.stderr)",
            ],
            "cwd": ".",
        },
    )

    assert result.success is True
    assert result.output["stderr"] == "problem\n"


def test_run_command_nonzero_exit_keeps_output(tmp_path) -> None:
    result = _registry(tmp_path).execute(
        "run_command",
        {
            "command": [
                sys.executable,
                "-c",
                "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)",
            ],
            "cwd": ".",
        },
    )

    assert result.success is False
    assert result.output["exit_code"] == 7
    assert result.output["stdout"] == "out\n"
    assert result.output["stderr"] == "err\n"
    assert "exited with code 7" in result.error


def test_run_command_uses_workspace_subdirectory_as_cwd(tmp_path) -> None:
    (tmp_path / "sub").mkdir()

    result = _registry(tmp_path).execute(
        "run_command",
        {
            "command": [
                sys.executable,
                "-c",
                "import pathlib; print(pathlib.Path.cwd().name)",
            ],
            "cwd": "sub",
        },
    )

    assert result.success is True
    assert result.output["cwd"] == "sub"
    assert result.output["stdout"] == "sub\n"


def test_run_command_rejects_cwd_traversal(tmp_path) -> None:
    result = _registry(tmp_path).execute(
        "run_command",
        {"command": [sys.executable, "-c", "print('x')"], "cwd": ".."},
    )

    assert result.success is False
    assert "traversal" in result.error


def test_run_command_rejects_outside_cwd(tmp_path) -> None:
    outside = tmp_path.parent

    result = _registry(tmp_path).execute(
        "run_command",
        {"command": [sys.executable, "-c", "print('x')"], "cwd": str(outside)},
    )

    assert result.success is False
    assert "outside" in result.error


def test_run_command_rejects_missing_cwd(tmp_path) -> None:
    result = _registry(tmp_path).execute(
        "run_command",
        {"command": [sys.executable, "-c", "print('x')"], "cwd": "missing"},
    )

    assert result.success is False
    assert "not found" in result.error


def test_run_command_rejects_file_cwd(tmp_path) -> None:
    (tmp_path / "file.txt").write_text("x", encoding="utf-8")

    result = _registry(tmp_path).execute(
        "run_command",
        {"command": [sys.executable, "-c", "print('x')"], "cwd": "file.txt"},
    )

    assert result.success is False
    assert "not a directory" in result.error


def test_run_command_timeout_returns_structured_result(tmp_path) -> None:
    result = _registry(tmp_path).execute(
        "run_command",
        {
            "command": [sys.executable, "-c", "import time; time.sleep(2)"],
            "cwd": ".",
            "timeout_seconds": 1,
        },
    )

    assert result.success is False
    assert result.output["timed_out"] is True
    assert result.output["exit_code"] is None
    assert "timed out" in result.error


def test_default_registry_passes_command_timeout_to_run_command(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path), command_timeout=1, allow_command=True)

    result = registry.execute(
        "run_command",
        {
            "command": [sys.executable, "-c", "import time; time.sleep(2)"],
            "cwd": ".",
        },
    )

    assert result.success is False
    assert result.output["timed_out"] is True
    assert "after 1 seconds" in result.error


def test_run_command_empty_command_is_rejected_by_validation(tmp_path) -> None:
    result = _registry(tmp_path).execute("run_command", {"command": [], "cwd": "."})

    assert result.success is False
    assert "Invalid parameters" in result.error


def test_command_policy_rejects_shell_true() -> None:
    decision = CommandPolicy().check([sys.executable, "--version"], use_shell=True)

    assert decision.allowed is False
    assert "shell=True" in decision.reason


def test_run_command_rejects_dangerous_command(tmp_path) -> None:
    result = _registry(tmp_path).execute("run_command", {"command": ["rm", "-rf", "x"], "cwd": "."})

    assert result.success is False
    assert result.output["exit_code"] is None
    assert "Dangerous command" in result.error


def test_run_command_rejects_shell_wrapper(tmp_path) -> None:
    result = _registry(tmp_path).execute(
        "run_command",
        {"command": ["cmd", "/c", "echo", "hello"], "cwd": "."},
    )

    assert result.success is False
    assert result.output["exit_code"] is None
    assert "Shell wrapper" in result.error


def test_run_command_rejects_shell_syntax_token(tmp_path) -> None:
    result = _registry(tmp_path).execute(
        "run_command",
        {"command": [sys.executable, "-c", "print('x')", "&&"], "cwd": "."},
    )

    assert result.success is False
    assert "Shell syntax token" in result.error


def test_run_command_truncates_long_output(tmp_path) -> None:
    result = _registry(tmp_path).execute(
        "run_command",
        {
            "command": [
                sys.executable,
                "-c",
                f"print('x' * {MAX_COMMAND_OUTPUT_CHARS + 1000})",
            ],
            "cwd": ".",
        },
    )

    assert result.success is True
    assert result.output["output_truncated"] is True
    assert "... output truncated ..." in result.output["stdout"]
    assert len(result.output["stdout"]) <= MAX_COMMAND_OUTPUT_CHARS
