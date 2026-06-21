from typer.testing import CliRunner

from codeharness.cli import app


runner = CliRunner()


def test_help_runs() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "CodeHarness" in result.output


def test_doctor_runs() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Python version:" in result.output
    assert "Config loaded: yes" in result.output


def test_run_accepts_task() -> None:
    task = "创建一个 hello.py"

    result = runner.invoke(app, ["run", task])

    assert result.exit_code == 0
    assert task in result.output
    assert "Agent Runtime 尚未实现" in result.output


def test_tools_command_runs() -> None:
    result = runner.invoke(app, ["tools"])

    assert result.exit_code == 0
    assert "list_files" in result.output
    assert "read_file" in result.output
    assert "write_file" in result.output
