"""Fake LLM client for tests and local demos."""

from __future__ import annotations

from collections.abc import Iterable


class FakeLLMClient:
    """Returns predefined text responses and records received prompts."""

    def __init__(self, responses: Iterable[str]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []
        self._index = 0

    def complete(self, prompt: str) -> str:
        """Return the next fake response."""

        self.prompts.append(prompt)
        if self._index >= len(self._responses):
            raise RuntimeError("FakeLLMClient has no response remaining.")

        response = self._responses[self._index]
        self._index += 1
        return response
