"""
executor.py — Builds the claude prompt string and runs it as a subprocess.

Supports two modes:
  - Streaming (default): pipes stdout line-by-line to the terminal in real time
  - Captured: collects output into a string (used by MCP server and parallel runner)

This is the layer that would become a tool-call in an MCP server:
  - Input:  agent name, task name, instruction string
  - Action: shell out to `claude --print --dangerously-skip-permissions`
  - Output: exit code + streamed/captured stdout
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import IO, Callable

from agent_runner.registry import resolve_agent, resolve_task


def build_prompt(agent: str, task: str, instruction: str) -> str:
    agent_file = resolve_agent(agent)
    task_file = resolve_task(task)
    return f"Read {agent_file} and {task_file}. {instruction} Run verification."


def run(agent: str, task: str, instruction: str, project_dir: Path) -> int:
    """
    Run a single agent with real-time streaming to the terminal.
    Returns the subprocess exit code.
    """
    prompt = build_prompt(agent, task, instruction)
    label = f"[{agent}]"

    sys.stderr.write(f"\n{'='*60}\n")
    sys.stderr.write(f"  {label} Starting: {task}\n")
    sys.stderr.write(f"  Instruction: {instruction}\n")
    sys.stderr.write(f"{'='*60}\n\n")
    sys.stderr.flush()

    start = time.monotonic()
    exit_code = _stream_subprocess(
        prompt=prompt,
        cwd=str(project_dir),
        line_callback=lambda line: _print_line(label, line, sys.stdout),
    )
    elapsed = time.monotonic() - start

    sys.stderr.write(f"\n{'='*60}\n")
    status = "completed" if exit_code == 0 else f"FAILED (exit {exit_code})"
    sys.stderr.write(f"  {label} {status} in {elapsed:.1f}s\n")
    sys.stderr.write(f"{'='*60}\n\n")
    sys.stderr.flush()

    return exit_code


def run_captured(
    agent: str,
    task: str,
    instruction: str,
    project_dir: Path,
    *,
    timeout: int = 300,
    line_callback: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    """
    Run a single agent, capturing all output into a string.
    Optionally calls line_callback(line) for each line as it arrives.
    Returns (exit_code, full_output). Returns (-1, partial) on timeout.
    """
    prompt = build_prompt(agent, task, instruction)
    lines: list[str] = []

    def _collect(line: str) -> None:
        lines.append(line)
        if line_callback:
            line_callback(line)

    exit_code = _stream_subprocess(
        prompt=prompt,
        cwd=str(project_dir),
        line_callback=_collect,
        timeout=timeout,
    )
    return exit_code, "".join(lines)


def _stream_subprocess(
    prompt: str,
    cwd: str,
    line_callback: Callable[[str], None],
    timeout: int | None = None,
) -> int:
    """
    Launch `claude` as a subprocess, feeding prompt via stdin,
    and call line_callback for every line of output in real time.
    Returns exit code (-1 on timeout).
    """
    proc = subprocess.Popen(
        "claude --print --dangerously-skip-permissions",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd,
        shell=True,
    )

    # Send prompt and close stdin so claude starts processing
    assert proc.stdin is not None
    proc.stdin.write(prompt)
    proc.stdin.close()

    # Stream stdout line by line
    assert proc.stdout is not None
    try:
        if timeout is not None:
            import threading

            timed_out = threading.Event()

            def _kill_on_timeout():
                if not timed_out.wait(timeout):
                    return
                proc.kill()

            timer = threading.Thread(target=_kill_on_timeout, daemon=True)
            timer.start()

        for line in proc.stdout:
            line_callback(line)

        proc.wait()

        if timeout is not None:
            timed_out.set()  # cancel the kill timer

        return proc.returncode if proc.returncode is not None else -1

    except Exception:
        proc.kill()
        proc.wait()
        return -1


def _print_line(label: str, line: str, stream: IO[str] = sys.stdout) -> None:
    """Write a prefixed line to the given stream."""
    # Strip trailing newline, add prefix, re-add newline
    text = line.rstrip("\n")
    if text:
        stream.write(f"{label} {text}\n")
        stream.flush()
