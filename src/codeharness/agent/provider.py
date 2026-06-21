"""Action providers for deterministic agent loops."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Protocol

from codeharness.agent.models import AgentAction, AgentContext


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
