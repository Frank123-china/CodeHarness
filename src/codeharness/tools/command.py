"""Workspace-limited command execution tool."""

from __future__ import annotations

import subprocess
import time
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from codeharness.safety import CommandPolicy
from codeharness.tools.base import BaseTool
from codeharness.tools.result import ToolResult
from codeharness.workspace import Workspace, WorkspaceAccessError

DEFAULT_COMMAND_TIMEOUT_SECONDS = 30
MAX_COMMAND_OUTPUT_CHARS = 20_000


class RunCommandArgs(BaseModel):
    """Arguments for running a command inside the workspace."""

    command: list[str] = Field(min_length=1)
    cwd: str = "."
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)

    @field_validator("command")
    @classmethod
    def command_parts_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if any(not part or not part.strip() for part in value):
            raise ValueError("command arguments must not be empty")
        return value


class RunCommandTool(BaseTool):
    """Run a subprocess command with workspace and policy checks."""

    name: ClassVar[str] = "run_command"
    description: ClassVar[str] = "Run a non-shell command inside the workspace."
    args_model: ClassVar[type[BaseModel]] = RunCommandArgs

    def __init__(
        self,
        policy: CommandPolicy | None = None,
        default_timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    ) -> None:
        self.policy = policy or CommandPolicy()
        self.default_timeout_seconds = default_timeout_seconds

    def execute(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        params = _cast_args(args, RunCommandArgs)
        timeout = params.timeout_seconds or self.default_timeout_seconds
        policy_decision = self.policy.check(params.command, use_shell=False)
        if not policy_decision.allowed:
            output = _result_payload(
                command=params.command,
                cwd=params.cwd,
                exit_code=None,
                stdout="",
                stderr="",
                timed_out=False,
                duration_ms=0,
                output_truncated=False,
            )
            return ToolResult.fail(
                policy_decision.reason or "Command rejected by policy.",
                output=output,
                metadata={"policy_rejected": True},
            )

        try:
            cwd_path = workspace.resolve_path(params.cwd)
            if not cwd_path.exists():
                return ToolResult.fail(f"Working directory not found: {params.cwd}", metadata={"cwd": params.cwd})
            if not cwd_path.is_dir():
                return ToolResult.fail(f"Working directory is not a directory: {params.cwd}", metadata={"cwd": params.cwd})
        except WorkspaceAccessError as exc:
            return ToolResult.fail(str(exc), metadata={"cwd": params.cwd})

        relative_cwd = workspace.relative_path(cwd_path)
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                params.command,
                cwd=str(cwd_path),
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = _duration_ms(started)
            stdout, stdout_truncated = _truncate_output(_to_text(exc.stdout))
            stderr, stderr_truncated = _truncate_output(_to_text(exc.stderr))
            output = _result_payload(
                command=params.command,
                cwd=relative_cwd,
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                timed_out=True,
                duration_ms=duration_ms,
                output_truncated=stdout_truncated or stderr_truncated,
            )
            return ToolResult.fail(
                f"Command timed out after {timeout} seconds.",
                output=output,
                metadata=output,
            )
        except FileNotFoundError:
            duration_ms = _duration_ms(started)
            output = _result_payload(
                command=params.command,
                cwd=relative_cwd,
                exit_code=None,
                stdout="",
                stderr="",
                timed_out=False,
                duration_ms=duration_ms,
                output_truncated=False,
            )
            return ToolResult.fail(
                f"Executable not found: {params.command[0]}",
                output=output,
                metadata=output,
            )
        except OSError as exc:
            duration_ms = _duration_ms(started)
            output = _result_payload(
                command=params.command,
                cwd=relative_cwd,
                exit_code=None,
                stdout="",
                stderr="",
                timed_out=False,
                duration_ms=duration_ms,
                output_truncated=False,
            )
            return ToolResult.fail(str(exc), output=output, metadata=output)

        duration_ms = _duration_ms(started)
        stdout, stdout_truncated = _truncate_output(completed.stdout)
        stderr, stderr_truncated = _truncate_output(completed.stderr)
        output = _result_payload(
            command=params.command,
            cwd=relative_cwd,
            exit_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
            duration_ms=duration_ms,
            output_truncated=stdout_truncated or stderr_truncated,
        )
        if completed.returncode == 0:
            return ToolResult.ok(output, metadata=output)
        return ToolResult.fail(
            f"Command exited with code {completed.returncode}.",
            output=output,
            metadata=output,
        )


def _cast_args(args: BaseModel, model: type[BaseModel]) -> BaseModel:
    if not isinstance(args, model):
        return model.model_validate(args)
    return args


def _duration_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _truncate_output(value: str) -> tuple[str, bool]:
    if len(value) <= MAX_COMMAND_OUTPUT_CHARS:
        return value, False

    marker = "\n... output truncated ...\n"
    keep = MAX_COMMAND_OUTPUT_CHARS - len(marker)
    head = keep // 2
    tail = keep - head
    return f"{value[:head]}{marker}{value[-tail:]}", True


def _result_payload(
    command: list[str],
    cwd: str,
    exit_code: int | None,
    stdout: str,
    stderr: str,
    timed_out: bool,
    duration_ms: int,
    output_truncated: bool,
) -> dict[str, object]:
    return {
        "command": command,
        "cwd": cwd,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "output_truncated": output_truncated,
    }
