"""Action providers for deterministic agent loops."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any, Protocol

from codeharness.agent.models import AgentAction, AgentContext
from codeharness.agent.prompt import PromptBuilder
from codeharness.llm.base import LLMClient
from codeharness.tools.registry import ToolRegistry


class LLMActionProviderError(ValueError):
    """Raised when an LLM response cannot be parsed into an AgentAction."""


class ActionProvider(Protocol):
    """Provides the next structured action for an AgentLoop."""

    def next_action(self, context: AgentContext) -> AgentAction:
        """Return the next action for the current context."""


class ScriptedActionProvider:
    """Returns predefined actions in order for tests and local demos."""

    def __init__(self, actions: Iterable[AgentAction | Mapping[str, Any]]) -> None:
        self._actions = [AgentAction.model_validate(action) for action in actions]
        self._index = 0

    def next_action(self, context: AgentContext) -> AgentAction:
        """Return the next scripted action, or finish when the script is exhausted."""

        if self._index >= len(self._actions):
            return AgentAction(type="finish", summary="No scripted actions remaining.")

        action = self._actions[self._index]
        self._index += 1
        return action.model_copy(deep=True)


class LLMActionProvider:
    """Builds prompts, calls an LLM client, and parses AgentAction JSON."""

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_builder: PromptBuilder,
        tool_registry: ToolRegistry,
    ) -> None:
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.tool_registry = tool_registry

    def next_action(self, context: AgentContext) -> AgentAction:
        """Return the next model-selected action."""

        prompt = self.prompt_builder.build(context, self.tool_registry.schemas())
        response = self.llm_client.complete(prompt)
        data = _parse_model_json(response)
        try:
            return AgentAction.model_validate(data)
        except ValueError as exc:
            raise LLMActionProviderError(f"Invalid agent action: {exc}") from exc


def _parse_model_json(response: str) -> object:
    text = _strip_json_fence(response)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMActionProviderError(f"Invalid JSON response: {exc}") from exc


def _strip_json_fence(response: str) -> str:
    text = response.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if len(lines) >= 3 and lines[0].strip().lower() in {"```", "```json"} and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return text
