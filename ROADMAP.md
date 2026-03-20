# Roadmap

## Phase 1 — Bash CLI wrapper ✅
`agent.sh` — run named agents against named task prompts from the terminal.

```bash
bash agent.sh run core add_strategy "Add a networking category"
bash agent.sh run core api --parallel "Add networking" "Add /categories" add_strategy add_endpoint
```

---

## Phase 2 — Python CLI ✅
Installable `agent` command built with Typer. Auto-generated `--help`, clean error messages, named flags for parallel runs, animated spinner.

```bash
agent run core add_strategy "Add a networking category"
agent run core add_strategy "Add networking" --parallel --agent2 api --task2 add_endpoint --instruction2 "Add /categories"
agent list
```

---

## Phase 3 — MCP Server 🔜
Wrap the executor as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server so Claude can call agents as tools directly, without a shell.

**What changes:**
- `registry.py` becomes the tool catalog (`@server.list_tools`)
- `executor.py` becomes a tool handler (`@server.call_tool`)
- The shell subprocess is replaced by direct Claude API calls
- Claude decides which agent to invoke based on context — you stop writing `agent run ...` manually

**Why it matters:**
This is the difference between you orchestrating Claude and Claude orchestrating itself.

---

## Phase 4 — Agent SDK Orchestration 🔜
Use the [Claude Agent SDK](https://docs.anthropic.com/claude/docs/agent-sdk) to build a multi-agent pipeline where a supervisor agent breaks down a task and dispatches sub-agents autonomously.

**What changes:**
- A supervisor agent receives a high-level goal (e.g. "add billing retry logic end-to-end")
- It determines which agents need to run and in what order
- Sub-agents (core, api, test) execute and report back
- The supervisor validates results and decides if re-runs are needed

**Why it matters:**
Phase 3 gives Claude access to tools. Phase 4 gives Claude judgment over when to use them.
