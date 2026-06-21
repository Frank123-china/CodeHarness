"""Structured tool execution results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Uniform result returned by every tool execution."""

    success: bool
    output: Any | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def ok(cls, output: Any | None = None, metadata: dict[str, Any] | None = None) -> "ToolResult":
        """Build a successful tool result."""

        return cls(success=True, output=output, metadata=metadata or {})

    @classmethod
    def fail(
        cls,
        error: str,
        output: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResult":
        """Build a failed tool result without raising to the caller."""

        return cls(success=False, output=output, error=error, metadata=metadata or {})
