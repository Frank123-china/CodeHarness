"""Workspace path safety helpers."""

from __future__ import annotations

import os
from pathlib import Path


class WorkspaceAccessError(ValueError):
    """Raised when a path attempts to escape the workspace."""


class Workspace:
    """Resolves paths while keeping all access inside one workspace root."""

    def __init__(self, root: str | Path) -> None:
        resolved = Path(root).expanduser().resolve(strict=True)
        if not resolved.is_dir():
            raise ValueError(f"Workspace root is not a directory: {resolved}")
        self.root = resolved

    def resolve_path(self, path: str | Path = ".") -> Path:
        """Resolve a relative or absolute path and ensure it stays in the workspace."""

        if str(path).strip() == "":
            raise WorkspaceAccessError("Path must not be empty.")

        raw_path = Path(path).expanduser()
        if ".." in raw_path.parts:
            raise WorkspaceAccessError("Path traversal is not allowed.")

        candidate = raw_path if raw_path.is_absolute() else self.root / raw_path
        resolved = candidate.resolve(strict=False)
        if not self.is_inside(resolved):
            raise WorkspaceAccessError("Path is outside the workspace.")
        return resolved

    def is_inside(self, path: str | Path) -> bool:
        """Return whether a path resolves inside the workspace root."""

        resolved = Path(path).expanduser().resolve(strict=False)
        root_text = os.path.normcase(str(self.root))
        target_text = os.path.normcase(str(resolved))
        try:
            return os.path.commonpath([root_text, target_text]) == root_text
        except ValueError:
            return False

    def relative_path(self, path: str | Path) -> str:
        """Return a workspace-relative path using forward slashes."""

        resolved = Path(path).expanduser().resolve(strict=False)
        if not self.is_inside(resolved):
            raise WorkspaceAccessError("Path is outside the workspace.")

        relative = os.path.relpath(str(resolved), str(self.root))
        if relative == ".":
            return "."
        return Path(relative).as_posix()
