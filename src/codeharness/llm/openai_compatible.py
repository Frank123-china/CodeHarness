"""OpenAI-compatible synchronous LLM client."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class LLMClientError(RuntimeError):
    """Raised when an LLM client request fails."""


class OpenAICompatibleClient:
    """Calls an OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 60,
        sdk_client: Any | None = None,
        sdk_client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self._api_key_for_redaction = api_key
        self._client = sdk_client or self._build_client(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            sdk_client_factory=sdk_client_factory,
        )

    def complete(self, prompt: str) -> str:
        """Return the first response message text for a prompt."""

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content
        except LLMClientError:
            raise
        except Exception as exc:
            raise LLMClientError(self._sanitize_error(f"LLM request failed: {exc}")) from exc

        if not isinstance(content, str) or not content:
            raise LLMClientError("LLM response did not contain text content.")
        return content

    def _build_client(
        self,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
        sdk_client_factory: Callable[..., Any] | None,
    ) -> Any:
        try:
            if sdk_client_factory is None:
                from openai import OpenAI

                sdk_client_factory = OpenAI
            return sdk_client_factory(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout_seconds,
                max_retries=0,
            )
        except Exception as exc:
            raise LLMClientError(self._sanitize_error(f"Failed to initialize LLM client: {exc}")) from exc

    def _sanitize_error(self, message: str) -> str:
        if self._api_key_for_redaction:
            return message.replace(self._api_key_for_redaction, "[redacted]")
        return message
