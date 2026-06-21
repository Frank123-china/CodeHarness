from codeharness.tools import create_default_registry
from codeharness.tools.files import MAX_TEXT_FILE_BYTES
from codeharness.workspace import Workspace


def test_list_files_lists_workspace_entries(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b", encoding="utf-8")
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("list_files", {"path": ".", "max_depth": 1})

    assert result.success is True
    assert "a.txt" in result.output
    assert "sub" in result.output
    assert "sub/b.txt" in result.output


def test_list_files_respects_max_depth(tmp_path) -> None:
    (tmp_path / "one" / "two").mkdir(parents=True)
    (tmp_path / "one" / "two" / "deep.txt").write_text("deep", encoding="utf-8")
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("list_files", {"path": ".", "max_depth": 0})

    assert result.success is True
    assert "one" in result.output
    assert "one/two" not in result.output
    assert "one/two/deep.txt" not in result.output


def test_list_files_ignores_common_directories(tmp_path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("hidden", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_text("hidden", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("visible", encoding="utf-8")
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("list_files", {"path": ".", "max_depth": 2})

    assert result.success is True
    assert "visible.txt" in result.output
    assert ".git" not in result.output
    assert "__pycache__" not in result.output


def test_list_files_rejects_outside_workspace(tmp_path) -> None:
    outside = tmp_path.parent / "outside-list"
    outside.mkdir(exist_ok=True)
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("list_files", {"path": str(outside), "max_depth": 1})

    assert result.success is False
    assert "outside" in result.error


def test_read_file_reads_utf8_file(tmp_path) -> None:
    (tmp_path / "hello.txt").write_text("hello", encoding="utf-8")
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("read_file", {"path": "hello.txt"})

    assert result.success is True
    assert result.output == "hello"
    assert result.metadata["path"] == "hello.txt"


def test_read_file_missing_file_returns_error(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("read_file", {"path": "missing.txt"})

    assert result.success is False
    assert "not found" in result.error


def test_read_file_directory_returns_error(tmp_path) -> None:
    (tmp_path / "folder").mkdir()
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("read_file", {"path": "folder"})

    assert result.success is False
    assert "directory" in result.error


def test_read_file_large_file_returns_error(tmp_path) -> None:
    (tmp_path / "large.txt").write_text("x" * (MAX_TEXT_FILE_BYTES + 1), encoding="utf-8")
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("read_file", {"path": "large.txt"})

    assert result.success is False
    assert "too large" in result.error


def test_read_file_rejects_outside_workspace(tmp_path) -> None:
    outside = tmp_path.parent / "outside-read.txt"
    outside.write_text("outside", encoding="utf-8")
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("read_file", {"path": str(outside)})

    assert result.success is False
    assert "outside" in result.error


def test_write_file_creates_file(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("write_file", {"path": "created.txt", "content": "hello"})

    assert result.success is True
    assert (tmp_path / "created.txt").read_text(encoding="utf-8") == "hello"
    assert result.output == {"path": "created.txt", "characters": 5}


def test_write_file_overwrites_file(tmp_path) -> None:
    (tmp_path / "created.txt").write_text("old", encoding="utf-8")
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("write_file", {"path": "created.txt", "content": "new"})

    assert result.success is True
    assert (tmp_path / "created.txt").read_text(encoding="utf-8") == "new"


def test_write_file_creates_parent_directories(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("write_file", {"path": "nested/new.txt", "content": "content"})

    assert result.success is True
    assert (tmp_path / "nested" / "new.txt").read_text(encoding="utf-8") == "content"
    assert result.metadata["characters"] == 7


def test_write_file_rejects_outside_workspace(tmp_path) -> None:
    outside = tmp_path.parent / "outside-write.txt"
    registry = create_default_registry(Workspace(tmp_path))

    result = registry.execute("write_file", {"path": str(outside), "content": "outside"})

    assert result.success is False
    assert "outside" in result.error
