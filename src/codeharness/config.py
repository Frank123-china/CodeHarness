"""Configuration models for CodeHarness."""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, Field


class CodeHarnessConfig(BaseModel):
    """Runtime configuration loaded from environment variables."""

    model_name: str = Field(default="gpt-4.1-mini")
    api_key: str | None = Field(default=None)
    base_url: str = Field(default="https://api.openai.com/v1")
    max_steps: int = Field(default=8, ge=1)
    command_timeout: int = Field(default=30, ge=1)

    @property
    def api_key_configured(self) -> bool:
        """Return whether an API key is available without exposing the value."""

        return bool(self.api_key)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "CodeHarnessConfig":
        """Load configuration from CODEHARNESS_* environment variables."""

        source = os.environ if environ is None else environ
        data: dict[str, str | None] = {}

        if model := _optional_value(source, "CODEHARNESS_MODEL"):
            data["model_name"] = model
        if api_key := _optional_value(source, "CODEHARNESS_API_KEY"):
            data["api_key"] = api_key
        if base_url := _optional_value(source, "CODEHARNESS_BASE_URL"):
            data["base_url"] = base_url
        if max_steps := _optional_value(source, "CODEHARNESS_MAX_STEPS"):
            data["max_steps"] = max_steps
        if timeout := _optional_value(source, "CODEHARNESS_COMMAND_TIMEOUT"):
            data["command_timeout"] = timeout

        return cls(**data)


def load_config() -> CodeHarnessConfig:
    """Load the default process configuration."""

    return CodeHarnessConfig.from_env()


def _optional_value(source: Mapping[str, str], name: str) -> str | None:
    value = source.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
