"""Minimal LLM client interface."""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Defines the smallest future interface for text model clients."""

    def complete(self, prompt: str) -> str:
        """Return a model response for a prompt."""

        raise NotImplementedError
