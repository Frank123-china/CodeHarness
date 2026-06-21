import os
from pathlib import Path

import pytest

from codeharness.workspace import Workspace, WorkspaceAccessError


def test_relative_path_resolves_inside_workspace(tmp_path) -> None:
    workspace = Workspace(tmp_path)

    resolved = workspace.resolve_path("notes/todo.txt")

    assert resolved == (tmp_path / "notes" / "todo.txt").resolve()


def test_absolute_path_inside_workspace_is_allowed(tmp_path) -> None:
    workspace = Workspace(tmp_path)
    target = tmp_path / "inside.txt"

    resolved = workspace.resolve_path(target)

    assert resolved == target.resolve()


def test_parent_traversal_is_rejected(tmp_path) -> None:
    workspace = Workspace(tmp_path)

    with pytest.raises(WorkspaceAccessError, match="traversal"):
        workspace.resolve_path("../outside.txt")


def test_absolute_path_outside_workspace_is_rejected(tmp_path) -> None:
    workspace = Workspace(tmp_path)
    outside = tmp_path.parent / "outside.txt"

    with pytest.raises(WorkspaceAccessError, match="outside"):
        workspace.resolve_path(outside)


@pytest.mark.skipif(os.name != "nt", reason="Windows path compatibility check")
def test_windows_style_relative_path_is_supported(tmp_path) -> None:
    workspace = Workspace(tmp_path)

    resolved = workspace.resolve_path(Path("nested\\file.txt"))

    assert resolved == (tmp_path / "nested" / "file.txt").resolve()
