# CodeHarness

CodeHarness is a lightweight Python CLI scaffold for a future programming agent inspired by Claude Code and Codex CLI.

The project is still in the framework stage. It can be installed, started, and tested. It currently includes a workspace-limited tool runtime, a deterministic AgentLoop driven by scripted actions, and a basic non-shell command execution tool. It does not call a real model.

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

## CLI Usage

Show help:

```powershell
code-harness --help
```

Check the local runtime:

```powershell
code-harness doctor
```

Pass a task to the placeholder runtime:

```powershell
code-harness run "创建并运行 hello.py"
```

List the registered development tools:

```powershell
code-harness tools
```

The original `CodeHarness` console command is also kept as a compatibility alias.

## Configuration

Configuration is read from environment variables:

```powershell
$env:CODEHARNESS_MODEL = "gpt-4.1-mini"
$env:CODEHARNESS_API_KEY = "your-api-key"
$env:CODEHARNESS_BASE_URL = "https://api.openai.com/v1"
$env:CODEHARNESS_MAX_STEPS = "8"
$env:CODEHARNESS_COMMAND_TIMEOUT = "30"
```

The API key is optional at this stage because CodeHarness does not call a real model yet.

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

Example runtime call:

```python
registry.execute(
    "run_command",
    {
        "command": ["python", "-c", "print('hello')"],
        "cwd": ".",
    },
)
```

The CLI only exposes a simple `tools` listing command. Tool execution is intended for internal/runtime use and tests at this stage.

## Command Safety

`run_command` always calls `subprocess.run(..., shell=False)` with a command argument list. Its `cwd` is resolved through `Workspace`, so path traversal and directories outside the workspace are rejected.

`CommandPolicy` provides basic protection by rejecting:

- empty commands or empty command arguments;
- `shell=True`;
- obvious dangerous commands such as `rm`, `rmdir`, `shutdown`, `format`, and similar system commands;
- shell wrappers such as `cmd`, `powershell`, `pwsh`, `bash`, and `sh`;
- common shell syntax tokens such as `&&`, `|`, `;`, and redirects.

This is not an operating-system-level sandbox. Commands still run with the current user's system permissions. Do not run arbitrary commands in an untrusted workspace.

## AgentLoop

CodeHarness includes a deterministic AgentLoop control layer:

- `AgentAction`: a Pydantic action model supporting `tool` and `finish`.
- `AgentStep`: one visible action and optional tool observation.
- `AgentRunResult`: the structured result for a run.
- `AgentContext`: the minimal context passed to an action provider.
- `ActionProvider`: a protocol for supplying actions.
- `ScriptedActionProvider`: a test/demo provider that returns predefined actions in order.

The AgentLoop only calls tools through `ToolRegistry`. It records tool failures as observations, stops on `finish`, returns `max_steps_exceeded` when the loop limit is reached, and returns `failed` when the provider raises an error or the task is empty.

## Testing

Run the test suite:

```powershell
python -m pytest
```

## Not Implemented Yet

CodeHarness does not yet include real model calls, an OpenAI client, prompt templates, an LLM action provider, shell command execution through shell wrappers, patch application, tool-calling protocol integration, Git automation, session persistence, checkpoints, automatic planning, retry strategies, user approval flows, Docker sandboxing, multi-agent behavior, long-term memory, MCP integration, databases, vector databases, a web UI, complex logging, or a complex permission system.
