import json

from codeharness.tools import create_default_registry
from codeharness.tools.files import ReadFileArgs
from codeharness.workspace import Workspace


def test_tool_schema_comes_from_pydantic_model(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path))
    schemas = {schema["name"]: schema for schema in registry.schemas()}

    assert schemas["read_file"]["parameters"] == ReadFileArgs.model_json_schema()
    assert schemas["read_file"]["description"] == "Read a UTF-8 text file inside the workspace."


def test_tool_schema_order_is_stable(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path), allow_all=True)

    names = [schema["name"] for schema in registry.schemas()]

    assert names == sorted(names)


def test_tool_schemas_are_json_serializable(tmp_path) -> None:
    registry = create_default_registry(Workspace(tmp_path), allow_all=True)

    encoded = json.dumps(registry.schemas(), ensure_ascii=False)

    assert "read_file" in encoded
    assert "run_command" in encoded
