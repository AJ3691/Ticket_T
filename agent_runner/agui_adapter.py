"""
agui_adapter.py — Async generator that translates subprocess execution into AG-UI events.

Wraps run_captured() (which calls the Claude CLI in a subprocess) so that each line
of output becomes a TextMessageContentEvent in an SSE stream consumed by the AG-UI
protocol. The subprocess runs in a background thread; the async side polls a queue.
"""

from __future__ import annotations

import asyncio
import queue
import threading
from pathlib import Path
from typing import AsyncGenerator
from uuid import uuid4

from ag_ui.core import (
    BaseEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)

from agent_runner.executor import run_captured
from agent_runner.registry import resolve_agent, resolve_task

PROJECT_DIR = Path(__file__).parent.parent.resolve()


async def agent_run_events(
    agent: str,
    task: str,
    instruction: str,
    thread_id: str,
    run_id: str,
) -> AsyncGenerator[BaseEvent, None]:
    """
    Async generator that yields AG-UI events for a single agent run.

    Event sequence on success:
        RunStartedEvent
        StepStartedEvent
        TextMessageStartEvent
        TextMessageContentEvent  (one per non-empty output line)
        ...
        TextMessageEndEvent
        StepFinishedEvent
        RunFinishedEvent

    On invalid agent/task:
        RunStartedEvent
        RunErrorEvent(code="INVALID_AGENT" | "INVALID_TASK")

    On non-zero subprocess exit:
        ... (content events) ...
        RunErrorEvent(code=str(exit_code))
    """
    yield RunStartedEvent(thread_id=thread_id, run_id=run_id)

    # Validate agent and task names before launching the subprocess.
    try:
        resolve_agent(agent)
    except ValueError as exc:
        yield RunErrorEvent(message=str(exc), code="INVALID_AGENT")
        return

    try:
        resolve_task(task)
    except ValueError as exc:
        yield RunErrorEvent(message=str(exc), code="INVALID_TASK")
        return

    step_name = f"{agent}:{task}"
    yield StepStartedEvent(step_name=step_name)

    message_id = uuid4().hex[:12]
    yield TextMessageStartEvent(message_id=message_id, role="assistant")

    # Run the subprocess in a background thread.
    # A queue bridges the thread's line_callback with the async poll loop.
    line_queue: queue.Queue[str] = queue.Queue()
    exit_code_container: list[int] = []

    def _run() -> None:
        code, _ = run_captured(
            agent,
            task,
            instruction,
            PROJECT_DIR,
            line_callback=line_queue.put,
        )
        exit_code_container.append(code)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    # Poll the queue while the thread is alive or items remain.
    while thread.is_alive() or not line_queue.empty():
        try:
            line = line_queue.get_nowait()
            stripped = line.rstrip("\n")
            if stripped:
                yield TextMessageContentEvent(message_id=message_id, delta=stripped)
        except queue.Empty:
            pass
        await asyncio.sleep(0.05)

    # Drain any lines that arrived after the thread finished.
    while not line_queue.empty():
        try:
            line = line_queue.get_nowait()
            stripped = line.rstrip("\n")
            if stripped:
                yield TextMessageContentEvent(message_id=message_id, delta=stripped)
        except queue.Empty:
            break

    yield TextMessageEndEvent(message_id=message_id)
    yield StepFinishedEvent(step_name=step_name)

    exit_code = exit_code_container[0] if exit_code_container else -1

    if exit_code == 0:
        yield RunFinishedEvent(thread_id=thread_id, run_id=run_id)
    else:
        yield RunErrorEvent(
            message=f"Agent '{agent}' failed (exit {exit_code})",
            code=str(exit_code),
        )
