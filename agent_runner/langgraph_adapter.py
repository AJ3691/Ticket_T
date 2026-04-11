"""
AG-UI adapter for the deterministic LangGraph triage proof of concept.

The adapter translates LangGraph state updates into AG-UI events so the existing
browser EventStream can render the graph run without knowing anything about
LangGraph internals.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator
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

from agent_runner.langgraph_triage import build_triage_graph


def _summarize_update(node_name: str, update: dict[str, Any]) -> str:
    if "category" in update:
        return f"[{node_name}] category: {update['category']}"

    if "recommendations" in update:
        count = len(update["recommendations"])
        return f"[{node_name}] drafted {count} recommendations"

    if "final_text" in update:
        return str(update["final_text"])

    return f"[{node_name}] updated state"


async def langgraph_triage_events(
    title: str,
    description: str,
    thread_id: str,
    run_id: str,
) -> AsyncGenerator[BaseEvent, None]:
    yield RunStartedEvent(thread_id=thread_id, run_id=run_id)

    message_id = uuid4().hex[:12]
    outer_step = "langgraph:triage"
    text_started = False

    try:
        yield StepStartedEvent(step_name=outer_step)
        yield TextMessageStartEvent(message_id=message_id, role="assistant")
        text_started = True

        graph = build_triage_graph()
        input_state = {"title": title, "description": description}

        async for chunk in graph.astream(input_state, stream_mode="updates"):
            for node_name, update in chunk.items():
                step_name = f"langgraph:{node_name}"
                yield StepStartedEvent(step_name=step_name)
                yield TextMessageContentEvent(
                    message_id=message_id,
                    delta=_summarize_update(node_name, update),
                )
                yield StepFinishedEvent(step_name=step_name)

        yield TextMessageEndEvent(message_id=message_id)
        yield StepFinishedEvent(step_name=outer_step)
        yield RunFinishedEvent(thread_id=thread_id, run_id=run_id)

    except Exception as exc:
        if text_started:
            yield TextMessageEndEvent(message_id=message_id)
            yield StepFinishedEvent(step_name=outer_step)
        yield RunErrorEvent(message=str(exc), code="LANGGRAPH_ERROR")
