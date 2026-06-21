# CodeHarness

[English](README.md) | [简体中文](README.zh-CN.md)

CodeHarness is a lightweight Python CLI scaffold for a future programming agent inspired by Claude Code and Codex CLI.

The project currently includes a workspace-limited tool runtime, a deterministic AgentLoop, a basic non-shell command tool, a fake LLM path for tests, and a minimal OpenAI-compatible client for real model calls.

## Environment

Create the dedicated Conda environment:

```powershell
conda create -n CodeHarness python=3.11 -y
conda activate CodeHarness
python --version
python -c "import sys; print(sys.executable)"
python -m pip install --upgrade pip
```

If Conda is unavailable, use a local virtual environment instead:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -c "import sys; print(sys.executable)"
python -m pip install --upgrade pip
```

Do not create both environments for the same checkout.

## Installation

Install the project and development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

## Configuration

Configuration is read from environment variables:

```powershell
$env:CODEHARNESS_MODEL = "gpt-4.1-mini"
$env:CODEHARNESS_API_KEY = "your-api-key"
$env:CODEHARNESS_BASE_URL = "https://api.openai.com/v1"
$env:CODEHARNESS_MAX_STEPS = "8"
$env:CODEHARNESS_COMMAND_TIMEOUT = "30"
$env:CODEHARNESS_LLM_TIMEOUT = "60"
```

`CODEHARNESS_BASE_URL` can point to any OpenAI-compatible chat completions endpoint. The API key is only displayed as configured/not configured; CodeHarness does not print the key.

## CLI Usage

Show help:

```powershell
code-harness --help
```

Check local configuration:

```powershell
code-harness doctor
```

Run the model-backed AgentLoop in default read-only mode:

```powershell
code-harness run "分析当前仓库结构"
```

Allow file writes:

```powershell
code-harness run "创建 hello.py" --allow-write
```

Allow file writes and command execution:

```powershell
code-harness run "创建 hello.py 并执行验证" --allow-write --allow-command
```

List currently allowed tools:

```powershell
code-harness tools
code-harness tools --allow-write
code-harness tools --allow-write --allow-command
```

The original `CodeHarness` console command is also kept as a compatibility alias.

## Tool Runtime

CodeHarness includes a minimal tool runtime with:

- `ToolResult`: a structured result with `success`, `output`, `error`, and `metadata`.
- `BaseTool`: a small interface with a name, description, Pydantic argument model, and `execute` method.
- `ToolRegistry`: the only execution entry point for registering, looking up, validating, and running tools.
- `Workspace`: path resolution and safety checks that keep file access inside a configured workspace root.

Built-in tools:

- `list_files`: lists workspace files and directories, with depth limits and ignored common directories.
- `read_file`: reads UTF-8 text files inside the workspace with a size limit.
- `write_file`: creates or overwrites UTF-8 text files inside the workspace.
- `run_command`: runs a non-shell subprocess command inside the workspace and captures `stdout`, `stderr`, `exit_code`, timeout state, duration, and truncation state.

Each tool exports a schema through `registry.schemas()`. The `parameters` schema comes from the tool's Pydantic argument model via `model_json_schema()`, and schema output is sorted by tool name.

## Tool Permissions

The model does not receive every tool by default.

Default allowed tools:

- `list_files`
- `read_file`

Additional flags:

- `--allow-write` exposes and enables `write_file`.
- `--allow-command` exposes and enables `run_command`.

Permissions are enforced twice: prompt/schema generation only includes currently allowed tools, and `ToolRegistry.execute()` rejects registered-but-disallowed tools with a structured `ToolResult`.

## Command Safety

`run_command` always calls `subprocess.run(..., shell=False)` with a command argument list. Its `cwd` is resolved through `Workspace`, so path traversal and directories outside the workspace are rejected.

`CommandPolicy` provides basic protection by rejecting:

- empty commands or empty command arguments;
- `shell=True`;
- obvious dangerous commands such as `rm`, `rmdir`, `shutdown`, `format`, and similar system commands;
- shell wrappers such as `cmd`, `powershell`, `pwsh`, `bash`, and `sh`;
- common shell syntax tokens such as `&&`, `|`, `;`, and redirects.

This is not an operating-system-level sandbox. Commands still run with the current user's system permissions. Do not run arbitrary commands in an untrusted workspace.

CodeHarness currently has no per-tool interactive approval, no Docker sandbox, and no session resume.

## LLM Runtime

`OpenAICompatibleClient` uses the official `openai` Python SDK and calls the synchronous Chat Completions API with one user message containing the prompt. It sets SDK retries to zero and maps SDK/network/auth/server failures into `LLMClientError` without including the API key in error messages.

The model response is parsed by `LLMActionProvider` as one JSON object:

```json
{"type":"tool","tool_name":"read_file","arguments":{"path":"README.md"}}
```

or:

```json
{"type":"finish","summary":"Task completed and verified."}
```

Invalid JSON or invalid fields become provider errors. Unknown tool names are not rewritten by the provider; they flow to `ToolRegistry`, which returns a structured tool failure observation.

## Testing

Run the test suite:

```powershell
python -m pytest
```

Automated tests use `FakeLLMClient` or injected SDK mocks and do not require network access or a real API key.

## Not Implemented Yet

CodeHarness does not yet include streaming output, async execution, automatic retries, JSON auto-repair, session persistence, resume, patch application, Git checkpoints, file backups, per-tool interactive approval, Docker sandboxing, network isolation, context compression, multi-agent behavior, long-term memory, MCP integration, databases, vector databases, a web UI, or complex logging.
