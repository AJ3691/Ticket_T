"""
executor.py — Builds the claude prompt string and runs it as a subprocess.

This is the layer that would become a tool-call in an MCP server:
  - Input:  agent name, task name, instruction string
  - Action: shell out to `claude --print --dangerously-skip-permissions`
  - Output: exit code + stdout/stderr streamed to terminal
"""

import subprocess
import sys
from pathlib import Path

from agent_runner.registry import resolve_agent, resolve_task
from agent_runner.spinner import Spinner


def build_prompt(agent: str, task: str, instruction: str) -> str:
    agent_file = resolve_agent(agent)
    task_file = resolve_task(task)
    return f"Read {agent_file} and {task_file}. {instruction} Run verification."


def run(agent: str, task: str, instruction: str, project_dir: Path) -> int:
    """
    Run a single agent synchronously.
    Streams output directly to the terminal.
    Returns the subprocess exit code.
    """
    prompt = build_prompt(agent, task, instruction)
    cmd = ["claude", "--print", "--dangerously-skip-permissions", prompt]

    with Spinner(f"Running [{agent}] {task}"):
        result = subprocess.run(cmd, cwd=str(project_dir), shell=True)
    return result.returncode
