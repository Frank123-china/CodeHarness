"""Basic command execution policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandPolicyDecision:
    """A policy decision for a command request."""

    allowed: bool
    reason: str | None = None


class CommandPolicy:
    """Provides basic guardrails before running subprocess commands."""

    SHELL_EXECUTABLES = {
        "bash",
        "cmd",
        "cmd.exe",
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe",
        "sh",
        "sh.exe",
    }
    DANGEROUS_EXECUTABLES = {
        "del",
        "diskpart",
        "erase",
        "format",
        "halt",
        "mkfs",
        "poweroff",
        "reboot",
        "reg",
        "rm",
        "rmdir",
        "shutdown",
    }
    SHELL_SYNTAX_TOKENS = {"&&", "||", "|", ";", ">", ">>", "<", "2>", "2>>"}

    def check(self, command: list[str], use_shell: bool = False) -> CommandPolicyDecision:
        """Return whether a command is allowed by the basic policy."""

        if use_shell:
            return CommandPolicyDecision(False, "shell=True is not allowed.")
        if not command:
            return CommandPolicyDecision(False, "Command must not be empty.")
        if any(not part or not part.strip() for part in command):
            return CommandPolicyDecision(False, "Command arguments must not be empty.")

        executable = _normalize_executable(command[0])
        if executable in self.SHELL_EXECUTABLES:
            return CommandPolicyDecision(False, f"Shell wrapper is not allowed: {command[0]}")
        if executable in self.DANGEROUS_EXECUTABLES:
            return CommandPolicyDecision(False, f"Dangerous command is not allowed: {command[0]}")

        for part in command:
            if part in self.SHELL_SYNTAX_TOKENS:
                return CommandPolicyDecision(False, f"Shell syntax token is not allowed: {part}")

        return CommandPolicyDecision(True)


def _normalize_executable(value: str) -> str:
    name = Path(value).name.lower()
    if name.endswith((".bat", ".cmd", ".com", ".exe")):
        return name[:-4]
    return name
