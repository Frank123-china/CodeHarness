"""Session recorder placeholder."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class SessionRecorder:
    """Accepts future session events without persisting them yet."""

    def record_event(self, event_type: str, payload: Mapping[str, Any] | None = None) -> None:
        """Reserve the future session recording entry point."""

        return None
