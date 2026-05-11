"""
tests/test_agui_phase1.py — Phase 1 tests for the AG-UI adapter and server.

Adapter tests (unit):
    - Valid agent emits RUN_STARTED as first event
    - Invalid agent emits RUN_ERROR with code INVALID_AGENT
    - Invalid task emits RUN_ERROR with code INVALID_TASK
    - Full event sequence for a successful run
    - Failed agent (exit code 1) emits RUN_ERROR as last event
    - All TextMessage events for one run share the same message_id

Server tests (integration):
    - GET /health → 200 + expected JSON
    - GET /agents → 200 + "agents" and "tasks" keys
    - POST /agui valid input → text/event-stream with RUN_STARTED + RUN_FINISHED
    - POST /agui invalid agent → RUN_ERROR in stream
    - OPTIONS /agui returns CORS headers
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio

from ag_ui.core import (
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from agui_server import app
from agent_runner.agui_adapter import agent_run_events


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_run_captured(lines: list[str], exit_code: int = 0):
    """
    Return a mock for run_captured that delivers lines via line_callback
    and returns the specified exit code.
    """
    def _mock(agent, task, instruction, project_dir, *, timeout=300, line_callback=None):
        for line in lines:
            if line_callback:
                line_callback(line)
        return exit_code, "".join(lines)
    return _mock


async def _collect_events(gen: AsyncGenerator) -> list:
    events = []
    async for event in gen:
        events.append(event)
    return events


def _parse_sse_events(body: bytes) -> list[dict]:
    """Parse SSE body into a list of event dicts."""
    events = []
    for line in body.decode().splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# ---------------------------------------------------------------------------
# Adapter unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adapter_valid_agent_emits_run_started():
    """First event from a valid run must be RunStartedEvent."""
    mock = _make_mock_run_captured(["hello\n"], exit_code=0)
    with patch("agent_runner.agui_adapter.run_captured", mock):
        events = await _collect_events(
            agent_run_events("core", "add_strategy", "test", "t1", "r1")
        )
    assert isinstance(events[0], RunStartedEvent)
    assert events[0].thread_id == "t1"
    assert events[0].run_id == "r1"


@pytest.mark.asyncio
async def test_adapter_invalid_agent_emits_error():
    """Unknown agent → RunStartedEvent then RunErrorEvent(code=INVALID_AGENT)."""
    events = await _collect_events(
        agent_run_events("nonexistent", "add_strategy", "test", "t1", "r1")
    )
    assert isinstance(events[0], RunStartedEvent)
    error = events[1]
    assert isinstance(error, RunErrorEvent)
    assert error.code == "INVALID_AGENT"


@pytest.mark.asyncio
async def test_adapter_invalid_task_emits_error():
    """Unknown task → RunStartedEvent then RunErrorEvent(code=INVALID_TASK)."""
    events = await _collect_events(
        agent_run_events("core", "nonexistent_task", "test", "t1", "r1")
    )
    assert isinstance(events[0], RunStartedEvent)
    error = events[1]
    assert isinstance(error, RunErrorEvent)
    assert error.code == "INVALID_TASK"


@pytest.mark.asyncio
async def test_adapter_event_sequence():
    """
    Three output lines → correct full sequence:
        RunStarted → StepStarted → TextStart → 3×TextContent → TextEnd → StepFinished → RunFinished
    """
    lines = ["line one\n", "line two\n", "line three\n"]
    mock = _make_mock_run_captured(lines, exit_code=0)
    with patch("agent_runner.agui_adapter.run_captured", mock):
        events = await _collect_events(
            agent_run_events("core", "add_strategy", "test", "t1", "r1")
        )

    types = [type(e) for e in events]
    assert types == [
        RunStartedEvent,
        StepStartedEvent,
        TextMessageStartEvent,
        TextMessageContentEvent,
        TextMessageContentEvent,
        TextMessageContentEvent,
        TextMessageEndEvent,
        StepFinishedEvent,
        RunFinishedEvent,
    ]

    # Verify content deltas
    content_events = [e for e in events if isinstance(e, TextMessageContentEvent)]
    assert [e.delta for e in content_events] == ["line one", "line two", "line three"]


@pytest.mark.asyncio
async def test_adapter_failed_agent_emits_run_error():
    """Non-zero exit code → last event is RunErrorEvent, not RunFinishedEvent."""
    mock = _make_mock_run_captured(["error output\n"], exit_code=1)
    with patch("agent_runner.agui_adapter.run_captured", mock):
        events = await _collect_events(
            agent_run_events("core", "add_strategy", "test", "t1", "r1")
        )
    assert isinstance(events[-1], RunErrorEvent)
    assert events[-1].code == "1"
    assert not any(isinstance(e, RunFinishedEvent) for e in events)


@pytest.mark.asyncio
async def test_adapter_message_id_consistent():
    """All TextMessage events in one run share the same message_id."""
    mock = _make_mock_run_captured(["a\n", "b\n"], exit_code=0)
    with patch("agent_runner.agui_adapter.run_captured", mock):
        events = await _collect_events(
            agent_run_events("core", "add_strategy", "test", "t1", "r1")
        )

    text_events = [
        e for e in events
        if isinstance(e, (TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent))
    ]
    assert len(text_events) > 0
    ids = {e.message_id for e in text_events}
    assert len(ids) == 1, f"Expected one message_id, got: {ids}"


# ---------------------------------------------------------------------------
# Server integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agui-agent-runner"}


@pytest.mark.asyncio
async def test_agents_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/agents")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert "tasks" in data
    assert "core" in data["agents"]
    assert "add_strategy" in data["tasks"]


@pytest.mark.asyncio
async def test_agui_endpoint_returns_sse():
    """Valid POST /agui returns text/event-stream with RUN_STARTED and RUN_FINISHED."""
    mock = _make_mock_run_captured(["output line\n"], exit_code=0)
    with patch("agent_runner.agui_adapter.run_captured", mock):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/agui",
                json={
                    "threadId": "t1",
                    "runId": "r1",
                    "agent": "core",
                    "task": "add_strategy",
                    "instruction": "test instruction",
                },
            )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = _parse_sse_events(response.content)
    event_types = [e.get("type") for e in events]
    assert "RUN_STARTED" in event_types
    assert "RUN_FINISHED" in event_types


@pytest.mark.asyncio
async def test_agui_endpoint_invalid_agent():
    """POST /agui with unknown agent → response stream contains RUN_ERROR."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/agui",
            json={
                "threadId": "t1",
                "runId": "r1",
                "agent": "bogus_agent",
                "task": "add_strategy",
                "instruction": "test",
            },
        )

    assert response.status_code == 200
    events = _parse_sse_events(response.content)
    event_types = [e.get("type") for e in events]
    assert "RUN_ERROR" in event_types

    error_event = next(e for e in events if e.get("type") == "RUN_ERROR")
    assert error_event.get("code") == "INVALID_AGENT"


@pytest.mark.asyncio
async def test_agui_cors_headers():
    """OPTIONS /agui returns CORS allow-origin header."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.options(
            "/agui",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "*"
