import json
import sys

from codeharness.agent import AgentAction, AgentLoop, LLMActionProvider, PromptBuilder
from codeharness.llm import FakeLLMClient
from codeharness.tools import create_default_registry
from codeharness.workspace import Workspace


def _provider(tmp_path, responses):
    client = FakeLLMClient(responses)
    registry = create_default_registry(Workspace(tmp_path), command_timeout=5, allow_all=True)
    provider = LLMActionProvider(client, PromptBuilder(), registry)
    return client, registry, provider


def test_tool_json_can_be_parsed(tmp_path) -> None:
    client, _, provider = _provider(
        tmp_path,
        ['{"type":"tool","tool_name":"read_file","arguments":{"path":"README.md"}}'],
    )

    action = provider.next_action(_context())

    assert action.type == "tool"
    assert action.tool_name == "read_file"
    assert action.arguments == {"path": "README.md"}
    assert len(client.prompts) == 1


def test_finish_json_can_be_parsed(tmp_path) -> None:
    _, _, provider = _provider(tmp_path, ['{"type":"finish","summary":"done"}'])

    action = provider.next_action(_context())

    assert action.type == "finish"
    assert action.summary == "done"


def test_json_markdown_fence_can_be_cleaned(tmp_path) -> None:
    _, _, provider = _provider(
        tmp_path,
        ['```json\n{"type":"finish","summary":"done"}\n```'],
    )

    action = provider.next_action(_context())

    assert action.type == "finish"
    assert action.summary == "done"


def test_invalid_json_becomes_provider_error(tmp_path) -> None:
    _, registry, provider = _provider(tmp_path, ["not json"])
    loop = AgentLoop(registry, provider)

    result = loop.run("parse bad JSON")

    assert result.status == "failed"
    assert result.stop_reason == "provider_error"
    assert "Invalid JSON response" in result.error


def test_missing_tool_name_becomes_provider_error(tmp_path) -> None:
    _, registry, provider = _provider(tmp_path, ['{"type":"tool","arguments":{}}'])
    loop = AgentLoop(registry, provider)

    result = loop.run("missing tool name")

    assert result.status == "failed"
    assert "tool_name is required" in result.error


def test_finish_missing_summary_becomes_provider_error(tmp_path) -> None:
    _, registry, provider = _provider(tmp_path, ['{"type":"finish"}'])
    loop = AgentLoop(registry, provider)

    result = loop.run("missing finish summary")

    assert result.status == "failed"
    assert "summary is required" in result.error


def test_unsupported_action_type_is_rejected(tmp_path) -> None:
    _, registry, provider = _provider(tmp_path, ['{"type":"think","summary":"nope"}'])
    loop = AgentLoop(registry, provider)

    result = loop.run("unsupported action")

    assert result.status == "failed"
    assert "Invalid agent action" in result.error


def test_fake_llm_exhaustion_becomes_provider_error(tmp_path) -> None:
    _, registry, provider = _provider(tmp_path, [])
    loop = AgentLoop(registry, provider)

    result = loop.run("exhaust fake LLM")

    assert result.status == "failed"
    assert result.stop_reason == "provider_error"
    assert "no response remaining" in result.error


def test_unknown_tool_is_left_for_registry_observation(tmp_path) -> None:
    client, registry, provider = _provider(
        tmp_path,
        [
            '{"type":"tool","tool_name":"not_a_tool","arguments":{}}',
            '{"type":"finish","summary":"done"}',
        ],
    )
    loop = AgentLoop(registry, provider)

    result = loop.run("call unknown tool")

    assert result.status == "completed"
    assert result.steps[0].tool_result.success is False
    assert "Unknown tool" in result.steps[0].tool_result.error
    assert "Unknown tool" in client.prompts[1]


def test_tool_failure_appears_in_next_prompt(tmp_path) -> None:
    client, registry, provider = _provider(
        tmp_path,
        [
            '{"type":"tool","tool_name":"read_file","arguments":{"path":"missing.txt"}}',
            '{"type":"finish","summary":"done"}',
        ],
    )
    loop = AgentLoop(registry, provider)

    result = loop.run("read missing file")

    assert result.status == "completed"
    assert "read_file" in client.prompts[1]
    assert "missing.txt" in client.prompts[1]
    assert "File not found" in client.prompts[1]


def test_prompt_contains_task_tools_and_history_without_sensitive_config(tmp_path) -> None:
    client, registry, provider = _provider(
        tmp_path,
        [
            '{"type":"tool","tool_name":"list_files","arguments":{"path":"."}}',
            '{"type":"finish","summary":"done"}',
        ],
    )
    loop = AgentLoop(registry, provider)

    result = loop.run("list files safely")

    assert result.status == "completed"
    first_prompt = client.prompts[0]
    second_prompt = client.prompts[1]
    assert "list files safely" in first_prompt
    assert "Available tools JSON Schema" in first_prompt
    assert "list_files" in first_prompt
    assert "Previous observable steps" in first_prompt
    assert "list_files" in second_prompt
    assert "api_key" not in first_prompt.lower()
    assert "CODEHARNESS_API_KEY" not in first_prompt


def test_fake_llm_full_integration(tmp_path) -> None:
    responses = [
        json.dumps({"type": "tool", "tool_name": "list_files", "arguments": {"path": ".", "max_depth": 1}}),
        json.dumps(
            {
                "type": "tool",
                "tool_name": "write_file",
                "arguments": {"path": "hello.py", "content": "print('Hello, CodeHarness')\n"},
            }
        ),
        json.dumps(
            {
                "type": "tool",
                "tool_name": "run_command",
                "arguments": {"command": [sys.executable, "hello.py"], "cwd": "."},
            }
        ),
        json.dumps({"type": "finish", "summary": "Task completed and verified."}),
    ]
    client, registry, provider = _provider(tmp_path, responses)
    loop = AgentLoop(registry, provider, max_steps=6)

    result = loop.run("create and run hello.py")

    assert result.status == "completed"
    assert (tmp_path / "hello.py").read_text(encoding="utf-8") == "print('Hello, CodeHarness')\n"
    assert result.steps[2].action.tool_name == "run_command"
    assert result.steps[2].tool_result.output["exit_code"] == 0
    assert "Hello, CodeHarness" in result.steps[2].tool_result.output["stdout"]
    assert len(result.steps) == 4
    assert len(client.prompts) == 4
    assert "write_file" in client.prompts[2]
    assert "Hello, CodeHarness" in client.prompts[3]


def _context():
    from codeharness.agent import AgentContext

    return AgentContext(task="test task", current_step=0)
