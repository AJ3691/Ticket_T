# CLI Reference — Python Agent Harness

## What this is

Phase 1 gave you `agent.sh` — a bash script to run agents by name.

Phase 2 replaces it with a proper Python CLI called `agent`. It does the same thing but with:
- Auto-generated `--help` on every command
- Clean error messages when you mistype an agent or task name
- A `--parallel` flag to run two agents at the same time
- An installable command (`agent`) that works anywhere in your shell

---

## What each file does

```
agent_runner/
├── __init__.py       empty — makes this a Python package
├── registry.py       the list of known agents and tasks
├── executor.py       runs one agent (builds the prompt, calls claude)
├── parallel.py       runs multiple agents at the same time using threads
└── cli.py            the command-line interface (Typer app)
```

### registry.py — the catalog

This is the single source of truth for agent and task names.

```python
AGENTS = {
    "core":   "agents/agent_core.md",
    "api":    "agents/agent_api.md",
    "schema": "agents/agent_schema.md",
    "test":   "agents/agent_tests.md",
}

TASKS = {
    "add_strategy":  "prompts/add_strategy.md",
    "add_endpoint":  "prompts/add_endpoint.md",
    ...
}
```

When you type `agent run core add_strategy`, the registry looks up:
- `core` → `agents/agent_core.md` (the agent's system prompt / rules)
- `add_strategy` → `prompts/add_strategy.md` (the task instructions)

To add a new agent: drop a `.md` file in `agents/` and add one line here.
To add a new task: drop a `.md` file in `prompts/` and add one line here.

---

### executor.py — runs one agent

Builds a single prompt string and shells out to `claude`:

```
"Read agents/agent_core.md and prompts/add_strategy.md. <your instruction> Run verification."
```

Then runs:
```
claude --print --dangerously-skip-permissions "<prompt>"
```

`--print` tells Claude to run non-interactively and print output to the terminal.
`--dangerously-skip-permissions` skips the confirmation prompts so it can run in a script.

---

### parallel.py — runs multiple agents at once

Uses Python **threads** — each thread gets its own subprocess running a different Claude agent.

```
Thread 1  →  claude (core agent)  → writes to app/rules/keyword.py
Thread 2  →  claude (api agent)   → writes to app/main.py
           ↓                            ↓
         wait for both to finish
           ↓
       collect exit codes → print summary
```

Why threads and not `asyncio`? Because `subprocess.run()` is blocking — threads are the right tool for blocking I/O. `asyncio` would need a different subprocess API.

---

### cli.py — the interface

Built with [Typer](https://typer.tiangolo.com/), which turns Python functions into CLI commands.

```python
@app.command(name="run")
def run_cmd(agent, task, instruction, --parallel, --agent2, --task2, --instruction2):
    ...

@app.command(name="list")
def list_cmd():
    ...
```

Typer handles:
- Parsing arguments
- Generating `--help`
- Showing usage errors if required arguments are missing

The `agent` command is registered in `pyproject.toml`:
```toml
[project.scripts]
agent = "agent_runner.cli:main"
```

This is what makes `agent` work as a shell command after `pip install -e .`.

---

## How to install

```bash
pip install -e .
```

The `-e` means "editable" — the package is installed from your local files, so any edits to `agent_runner/` take effect immediately without reinstalling.

---

## How to use

```bash
# List all registered agents and tasks
agent list

# Run one agent
agent run core add_strategy "Add a networking category"
agent run api  add_endpoint "Add GET /categories"

# Run two agents in parallel (both run at the same time)
agent run core add_strategy "Add networking" \
  --parallel \
  --agent2 api \
  --task2 add_endpoint \
  --instruction2 "Add GET /categories"

# Help
agent --help
agent run --help
```

---

## What happens when you run `agent run core add_strategy "Add networking"`

1. CLI parses the arguments: `agent=core`, `task=add_strategy`, `instruction="Add networking"`
2. `registry.py` looks up `core` → `agents/agent_core.md`, `add_strategy` → `prompts/add_strategy.md`
3. `executor.py` builds the prompt:
   ```
   Read agents/agent_core.md and prompts/add_strategy.md. Add networking. Run verification.
   ```
4. `executor.py` runs `claude --print --dangerously-skip-permissions "<prompt>"`
5. Claude reads both files, does the work, writes the code, runs verification
6. Output streams to your terminal. Exit code is passed back to the shell.

---

## Why this matters — the MCP connection

This harness is the same architectural pattern as an MCP (Model Context Protocol) server:

| This CLI | MCP server |
|----------|------------|
| `registry.py` — maps names to files | Tool catalog — lists available tools |
| `executor.py` — builds prompt + runs claude | Tool handler — executes a tool call |
| `parallel.py` — runs multiple agents | Concurrent tool dispatch |
| `cli.py` — the interface | The MCP protocol layer |

The difference: in an MCP server, Claude calls your tools directly over a protocol instead of you calling Claude from the shell. But the registry → executor → result pattern is identical.

---

## Compared to agent.sh (Phase 1)

| | `agent.sh` (bash) | `agent` (Python CLI) |
|---|---|---|
| Help text | Manual `echo` | Auto-generated by Typer |
| Error messages | Basic `echo [ERROR]` | Structured with known names listed |
| Parallel syntax | Positional args, easy to get wrong | Named flags (`--agent2`, `--task2`) |
| Tab autocomplete | No | Yes (via `typer`) |
| Extensibility | Edit bash arrays | Edit Python dicts |
| Installable | No | Yes (`pip install -e .`) |

Both are kept in the repo — `agent.sh` as a reference, `agent` CLI as the production tool.
