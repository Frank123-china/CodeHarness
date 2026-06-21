"""Structured agent runtime models."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from codeharness.tools.result import ToolResult


class AgentAction(BaseModel):
    """A deterministic action selected by an ActionProvider."""

    type: Literal["tool", "finish"]
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None

    @model_validator(mode="after")
    def validate_action_fields(self) -> Self:
        if self.type == "tool" and not _has_text(self.tool_name):
            raise ValueError("tool_name is required for tool actions.")
        if self.type == "finish" and not _has_text(self.summary):
            raise ValueError("summary is required for finish actions.")
        return self


class AgentStep(BaseModel):
    """One visible action and observation from an agent loop."""

    step_number: int = Field(ge=1)
    action: AgentAction
    tool_result: ToolResult | None = None
    error: str | None = None


class AgentContext(BaseModel):
    """Minimal context passed to an ActionProvider."""

    task: str
    current_step: int = Field(ge=0)
    steps: list[AgentStep] = Field(default_factory=list)


class AgentRunResult(BaseModel):
    """Structured result for a complete agent run."""

    task: str
    status: Literal["completed", "failed", "max_steps_exceeded"]
    summary: str | None = None
    steps: list[AgentStep] = Field(default_factory=list)
    stop_reason: str
    error: str | None = None


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())
