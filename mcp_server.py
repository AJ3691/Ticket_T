"""
mcp_server.py — Phase 3: MCP server wrapping the agent harness.

Claude Desktop connects to this server on startup (via stdio transport).
Claude can then call run_agent as a tool during any conversation.

How it works:
  1. Claude calls list_tools() once → sees what tools are available
  2. During conversation, Claude decides to call run_agent(agent, task, instruction)
  3. call_tool() runs the subprocess with captured output (not streamed —
     stdout is the MCP protocol channel in stdio mode)
  4. Full agent output + exit status is returned to Claude as text

Run manually to test:
  python mcp_server.py

Register in Claude Desktop:
  See claude_desktop_config.json in this directory.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from agent_runner.executor import build_prompt
from agent_runner.registry import AGENTS, TASKS

PROJECT_DIR = Path(__file__).parent.resolve()

# Maximum time (seconds) to wait for a single agent run.
# Claude CLI agents typically finish in 60-180s. Set generous upper bound.
AGENT_TIMEOUT = 300

server = Server("agent-harness")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Tell Claude what tools are available."""
    known_agents = ", ".join(sorted(AGENTS.keys()))
    known_tasks = ", ".join(sorted(TASKS.keys()))

    return [
        Tool(
            name="run_agent",
            description=(
                "Run a named Claude agent against a named task prompt. "
                "The agent reads its system prompt file and task instructions, "
                "then makes the requested code change and runs verification. "
                f"Known agents: {known_agents}. "
                f"Known tasks: {known_tasks}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "description": f"Agent name. One of: {known_agents}",
                    },
                    "task": {
                        "type": "string",
                        "description": f"Task name. One of: {known_tasks}",
                    },
                    "instruction": {
                        "type": "string",
                        "description": "Free-text instruction appended to the prompt.",
                    },
                },
                "required": ["agent", "task", "instruction"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool call from Claude."""
    if name != "run_agent":
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    agent = arguments.get("agent", "")
    task = arguments.get("task", "")
    instruction = arguments.get("instruction", "")

    # Validate inputs before running
    if agent not in AGENTS:
        known = ", ".join(sorted(AGENTS))
        return [TextContent(type="text", text=f"Unknown agent '{agent}'. Known agents: {known}")]

    if task not in TASKS:
        known = ", ".join(sorted(TASKS))
        return [TextContent(type="text", text=f"Unknown task '{task}'. Known tasks: {known}")]

    # Build the prompt that will be sent to the Claude CLI
    prompt = build_prompt(agent, task, instruction)

    def _run():
        log_file = PROJECT_DIR / ".agent_last_run.log"
        with open(log_file, "w", encoding="utf-8") as fh:
            try:
                # Pass the prompt via stdin to avoid shell quoting issues on
                # Windows.  shell=True + a list argument causes cmd.exe to
                # split the long prompt string on spaces, so the CLI never
                # receives it as a single argument.  Piping via stdin is the
                # reliable cross-platform approach.
                result = subprocess.run(
                    "claude --print --dangerously-skip-permissions",
                    input=prompt,
                    text=True,
                    cwd=str(PROJECT_DIR),
                    shell=True,
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    timeout=AGENT_TIMEOUT,
                )
                return result.returncode, None
            except subprocess.TimeoutExpired:
                return -1, "timeout"

    returncode, error = await asyncio.to_thread(_run)

    # Read the captured output (tail it to stay within MCP message limits)
    log_file = PROJECT_DIR / ".agent_last_run.log"
    output = ""
    if log_file.exists():
        raw = log_file.read_text(encoding="utf-8", errors="replace")
        # Keep last 4000 chars to avoid oversized MCP responses
        output = raw[-4000:] if len(raw) > 4000 else raw

    if error == "timeout":
        summary = (
            f"[{agent}] {task} TIMED OUT after {AGENT_TIMEOUT}s.\n"
            f"Instruction: {instruction}\n"
            f"Partial output may exist in .agent_last_run.log\n\n"
            f"--- tail of output ---\n{output}"
        )
    elif returncode == 0:
        summary = (
            f"[{agent}] {task} completed successfully (exit 0).\n"
            f"Instruction: {instruction}\n\n"
            f"--- agent output ---\n{output}"
        )
    else:
        summary = (
            f"[{agent}] {task} failed (exit {returncode}).\n"
            f"Instruction: {instruction}\n\n"
            f"--- agent output ---\n{output}"
        )

    return [TextContent(type="text", text=summary)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
