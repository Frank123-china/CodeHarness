"""Prompt construction for LLM-driven action selection."""

from __future__ import annotations

import json
from typing import Any

from codeharness.agent.models import AgentContext, AgentStep
from codeharness.tools.result import ToolResult


class PromptBuilder:
    """Builds a compact prompt from visible agent context and tool schemas."""

    def __init__(self, max_observation_chars: int = 4_000) -> None:
        self.max_observation_chars = max_observation_chars

    def build(self, context: AgentContext, tool_schemas: list[dict[str, object]]) -> str:
        """Build a prompt for the next model action."""

        history = [_step_to_observation(step, self.max_observation_chars) for step in context.steps]
        return "\n".join(
            [
                "You are CodeHarness, a deterministic coding agent controller.",
                "Return exactly one JSON object. Do not use Markdown fences or extra explanation.",
                "",
                "Allowed action formats:",
                '{"type":"tool","tool_name":"read_file","arguments":{"path":"README.md"}}',
                '{"type":"finish","summary":"Task completed and verified."}',
                "",
                f"Task: {context.task}",
                f"Current step: {context.current_step}",
                "",
                "Available tools JSON Schema:",
                json.dumps(tool_schemas, ensure_ascii=False, sort_keys=True),
                "",
                "Previous observable steps:",
                json.dumps(history, ensure_ascii=False, sort_keys=True),
            ]
        )


def _step_to_observation(step: AgentStep, max_chars: int) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "step_number": step.step_number,
        "action": step.action.model_dump(),
    }
    if step.tool_result is not None:
        observation["tool_result"] = _summarize_tool_result(step.tool_result, max_chars)
    if step.error:
        observation["error"] = step.error
    return observation


def _summarize_tool_result(result: ToolResult, max_chars: int) -> dict[str, Any]:
    return {
        "success": result.success,
        "output": _limit_value(result.output, max_chars),
        "error": _limit_value(result.error, max_chars),
        "metadata": _limit_value(result.metadata, max_chars),
    }


def _limit_value(value: Any, max_chars: int) -> Any:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) <= max_chars:
        return value
    marker = "... truncated ..."
    keep = max_chars - len(marker)
    if keep <= 0:
        return marker
    return f"{text[:keep]}{marker}"
