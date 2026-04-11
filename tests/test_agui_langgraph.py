from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from ag_ui.core import (
    RunFinishedEvent,
    RunStartedEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from agent_runner.langgraph_adapter import langgraph_triage_events
from agent_runner.langgraph_triage import build_triage_graph
from agui_server import app


async def _collect_events(gen):
    events = []
    async for event in gen:
        events.append(event)
    return events


def _parse_sse_events(body: bytes) -> list[dict]:
    events = []
    for line in body.decode().splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_langgraph_graph_returns_final_text():
    graph = build_triage_graph()
    result = graph.invoke(
        {
            "title": "Cannot log in",
            "description": "Password reset token expired",
        }
    )

    assert result["category"] == "account_access"
    assert "Recommendations:" in result["final_text"]
    assert len(result["recommendations"]) == 3


def test_langgraph_graph_is_deterministic():
    graph = build_triage_graph()
    input_state = {
        "title": "VPN timeout",
        "description": "Connection to the API fails through the proxy",
    }

    assert graph.invoke(input_state) == graph.invoke(input_state)


@pytest.mark.asyncio
async def test_langgraph_adapter_emits_run_started():
    events = await _collect_events(
        langgraph_triage_events("Cannot log in", "Password reset failed", "t1", "r1")
    )

    assert isinstance(events[0], RunStartedEvent)
    assert events[0].thread_id == "t1"
    assert events[0].run_id == "r1"


@pytest.mark.asyncio
async def test_langgraph_adapter_emits_text_content():
    events = await _collect_events(
        langgraph_triage_events("Cannot log in", "Password reset failed", "t1", "r1")
    )
    content = [event for event in events if isinstance(event, TextMessageContentEvent)]

    assert content
    assert any("category: account_access" in event.delta for event in content)
    assert any("Recommendations:" in event.delta for event in content)


@pytest.mark.asyncio
async def test_langgraph_adapter_event_sequence():
    events = await _collect_events(
        langgraph_triage_events("VPN timeout", "Proxy connection error", "t1", "r1")
    )

    assert isinstance(events[0], RunStartedEvent)
    assert isinstance(events[1], StepStartedEvent)
    assert isinstance(events[2], TextMessageStartEvent)
    assert any(isinstance(event, TextMessageContentEvent) for event in events)
    assert isinstance(events[-3], TextMessageEndEvent)
    assert isinstance(events[-2], StepFinishedEvent)
    assert isinstance(events[-1], RunFinishedEvent)


@pytest.mark.asyncio
async def test_langgraph_adapter_error():
    with patch("agent_runner.langgraph_adapter.build_triage_graph", side_effect=RuntimeError("boom")):
        events = await _collect_events(
            langgraph_triage_events("x", "y", "t1", "r1")
        )

    assert events[-1].type == "RUN_ERROR"
    assert events[-1].code == "LANGGRAPH_ERROR"


@pytest.mark.asyncio
async def test_langgraph_endpoint_returns_sse():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/agui/triage",
            json={
                "threadId": "t1",
                "runId": "r1",
                "title": "Cannot log in",
                "description": "Password reset token expired",
            },
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_langgraph_endpoint_contains_run_finished():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/agui/triage",
            json={
                "threadId": "t1",
                "runId": "r1",
                "title": "VPN timeout",
                "description": "Connection through proxy fails",
            },
        )

    events = _parse_sse_events(response.content)
    event_types = [event["type"] for event in events]

    assert "RUN_STARTED" in event_types
    assert "RUN_FINISHED" in event_types
    assert any(
        event.get("type") == "TEXT_MESSAGE_CONTENT"
        and "category: networking" in event.get("delta", "")
        for event in events
    )
