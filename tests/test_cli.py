from typer.testing import CliRunner

import codeharness.cli as cli_module
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
    assert "LLM timeout:" in result.output
    assert "API key configured:" in result.output


def test_run_without_api_key_exits_cleanly(monkeypatch) -> None:
    monkeypatch.delenv("CODEHARNESS_API_KEY", raising=False)
    task = "创建一个 hello.py"

    result = runner.invoke(app, ["run", task])

    assert result.exit_code == 1
    assert task in result.output
    assert "API key is not configured" in result.output
    assert "Traceback" not in result.output


def test_run_uses_agent_loop_when_api_key_is_configured(monkeypatch) -> None:
    class FakeOpenAICompatibleClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def complete(self, prompt: str) -> str:
            return '{"type":"finish","summary":"done from fake client"}'

    monkeypatch.setattr(cli_module, "OpenAICompatibleClient", FakeOpenAICompatibleClient)
    monkeypatch.setenv("CODEHARNESS_API_KEY", "test-key")

    result = runner.invoke(app, ["run", "分析当前项目"])

    assert result.exit_code == 0
    assert "Allowed tools: list_files, read_file" in result.output
    assert "Status: completed" in result.output
    assert "done from fake client" in result.output
    assert "test-key" not in result.output


def test_tools_command_defaults_to_read_only() -> None:
    result = runner.invoke(app, ["tools"])

    assert result.exit_code == 0
    assert "list_files" in result.output
    assert "read_file" in result.output
    assert "run_command" not in result.output
    assert "write_file" not in result.output


def test_tools_command_respects_permission_flags() -> None:
    result = runner.invoke(app, ["tools", "--allow-write", "--allow-command"])

    assert result.exit_code == 0
    assert "list_files" in result.output
    assert "read_file" in result.output
    assert "run_command" in result.output
    assert "write_file" in result.output
