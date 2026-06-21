"""Deterministic agent control loop."""

from __future__ import annotations

from codeharness.agent.models import AgentContext, AgentRunResult, AgentStep
from codeharness.agent.provider import ActionProvider
from codeharness.tools.registry import ToolRegistry


class AgentLoop:
    """Runs structured actions through ToolRegistry until finish or stop."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        action_provider: ActionProvider,
        max_steps: int = 8,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")
        self.tool_registry = tool_registry
        self.action_provider = action_provider
        self.max_steps = max_steps

    def run(self, task: str) -> AgentRunResult:
        """Run a deterministic action loop for a user task."""

        if not task.strip():
            return AgentRunResult(
                task=task,
                status="failed",
                summary=None,
                steps=[],
                stop_reason="empty_task",
                error="Task must not be empty.",
            )

        steps: list[AgentStep] = []
        for step_number in range(1, self.max_steps + 1):
            context = AgentContext(task=task, current_step=len(steps), steps=steps.copy())
            try:
                action = self.action_provider.next_action(context)
            except Exception as exc:
                return AgentRunResult(
                    task=task,
                    status="failed",
                    summary=None,
                    steps=steps,
                    stop_reason="provider_error",
                    error=str(exc),
                )

            if action.type == "finish":
                steps.append(AgentStep(step_number=step_number, action=action))
                return AgentRunResult(
                    task=task,
                    status="completed",
                    summary=action.summary,
                    steps=steps,
                    stop_reason="finish",
                    error=None,
                )

            tool_result = self.tool_registry.execute(action.tool_name or "", action.arguments)
            steps.append(
                AgentStep(
                    step_number=step_number,
                    action=action,
                    tool_result=tool_result,
                    error=tool_result.error if not tool_result.success else None,
                )
            )

        return AgentRunResult(
            task=task,
            status="max_steps_exceeded",
            summary=None,
            steps=steps,
            stop_reason="max_steps_exceeded",
            error=f"Maximum steps exceeded: {self.max_steps}",
        )
