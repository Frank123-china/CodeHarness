"""Workspace-limited file tools."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field

from codeharness.tools.base import BaseTool
from codeharness.tools.result import ToolResult
from codeharness.workspace import Workspace, WorkspaceAccessError

IGNORED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}
MAX_TEXT_FILE_BYTES = 1_000_000


class ListFilesArgs(BaseModel):
    """Arguments for listing workspace files."""

    path: str = "."
    max_depth: int = Field(default=2, ge=0, le=20)


class ReadFileArgs(BaseModel):
    """Arguments for reading a UTF-8 text file."""

    path: str = Field(min_length=1)


class WriteFileArgs(BaseModel):
    """Arguments for writing a UTF-8 text file."""

    path: str = Field(min_length=1)
    content: str


class ListFilesTool(BaseTool):
    """List files and directories below a workspace path."""

    name: ClassVar[str] = "list_files"
    description: ClassVar[str] = "List files and directories inside the workspace."
    args_model: ClassVar[type[BaseModel]] = ListFilesArgs

    def execute(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        params = _cast_args(args, ListFilesArgs)
        try:
            target = workspace.resolve_path(params.path)
            if not target.exists():
                return ToolResult.fail(
                    f"Directory not found: {params.path}",
                    metadata={"path": params.path},
                )
            if not target.is_dir():
                return ToolResult.fail(
                    f"Path is not a directory: {params.path}",
                    metadata={"path": workspace.relative_path(target)},
                )

            entries: list[str] = []
            self._collect_entries(target, workspace, params.max_depth, entries, current_depth=0)
            return ToolResult.ok(
                entries,
                metadata={
                    "path": workspace.relative_path(target),
                    "count": len(entries),
                    "max_depth": params.max_depth,
                },
            )
        except WorkspaceAccessError as exc:
            return ToolResult.fail(str(exc), metadata={"path": params.path})
        except OSError as exc:
            return ToolResult.fail(str(exc), metadata={"path": params.path})

    def _collect_entries(
        self,
        directory: Path,
        workspace: Workspace,
        max_depth: int,
        entries: list[str],
        current_depth: int,
    ) -> None:
        for child in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
            if child.is_dir() and child.name in IGNORED_DIRECTORIES:
                continue

            entries.append(workspace.relative_path(child))
            if child.is_dir() and current_depth < max_depth:
                self._collect_entries(child, workspace, max_depth, entries, current_depth + 1)


class ReadFileTool(BaseTool):
    """Read a UTF-8 text file from the workspace."""

    name: ClassVar[str] = "read_file"
    description: ClassVar[str] = "Read a UTF-8 text file inside the workspace."
    args_model: ClassVar[type[BaseModel]] = ReadFileArgs

    def execute(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        params = _cast_args(args, ReadFileArgs)
        try:
            target = workspace.resolve_path(params.path)
            if not target.exists():
                return ToolResult.fail(
                    f"File not found: {params.path}",
                    metadata={"path": params.path},
                )
            if target.is_dir():
                return ToolResult.fail(
                    f"Path is a directory: {params.path}",
                    metadata={"path": workspace.relative_path(target)},
                )

            size = target.stat().st_size
            if size > MAX_TEXT_FILE_BYTES:
                return ToolResult.fail(
                    f"File is too large to read: {size} bytes",
                    metadata={
                        "path": workspace.relative_path(target),
                        "bytes": size,
                        "limit": MAX_TEXT_FILE_BYTES,
                    },
                )

            content = target.read_text(encoding="utf-8")
            return ToolResult.ok(
                content,
                metadata={"path": workspace.relative_path(target), "bytes": size},
            )
        except UnicodeDecodeError as exc:
            return ToolResult.fail(f"File is not valid UTF-8: {exc}", metadata={"path": params.path})
        except WorkspaceAccessError as exc:
            return ToolResult.fail(str(exc), metadata={"path": params.path})
        except OSError as exc:
            return ToolResult.fail(str(exc), metadata={"path": params.path})


class WriteFileTool(BaseTool):
    """Create or overwrite a UTF-8 text file inside the workspace."""

    name: ClassVar[str] = "write_file"
    description: ClassVar[str] = "Create or overwrite a UTF-8 text file inside the workspace."
    args_model: ClassVar[type[BaseModel]] = WriteFileArgs

    def execute(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        params = _cast_args(args, WriteFileArgs)
        try:
            target = workspace.resolve_path(params.path)
            if target.exists() and target.is_dir():
                return ToolResult.fail(
                    f"Path is a directory: {params.path}",
                    metadata={"path": workspace.relative_path(target)},
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(params.content, encoding="utf-8")
            relative_path = workspace.relative_path(target)
            details = {"path": relative_path, "characters": len(params.content)}
            return ToolResult.ok(details, metadata=details)
        except WorkspaceAccessError as exc:
            return ToolResult.fail(str(exc), metadata={"path": params.path})
        except OSError as exc:
            return ToolResult.fail(str(exc), metadata={"path": params.path})


def _cast_args(args: BaseModel, model: type[BaseModel]) -> BaseModel:
    if not isinstance(args, model):
        return model.model_validate(args)
    return args
