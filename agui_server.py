"""
agui_server.py — FastAPI app exposing the AG-UI SSE endpoint for the agent runner.

Endpoints:
    GET  /health   — liveness check
    GET  /agents   — agent and task registries as JSON
    POST /agui     — accepts an agent run request, returns SSE stream of AG-UI events

Port is configured via the AGUI_PORT environment variable (default: 8002).

Run:
    uvicorn agui_server:app --reload --port $(python -c "import os; print(os.getenv('AGUI_PORT', 8002))")

Or simply:
    AGUI_PORT=8002 uvicorn agui_server:app --reload --port 8002
"""

from __future__ import annotations

import os

from ag_ui.encoder import EventEncoder
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import StreamingResponse

from agent_runner.agui_adapter import agent_run_events
from agent_runner.langgraph_adapter import langgraph_triage_events
from agent_runner.registry import AGENTS, TASKS

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="AG-UI Agent Runner", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Port is read at startup from the environment; used only when the module is
# run directly (uvicorn reads it from the CLI flag, not from here).
PORT: int = int(os.getenv("AGUI_PORT", "8002"))

encoder = EventEncoder()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AgentRunInput(BaseModel):
    thread_id: str = Field(alias="threadId")
    run_id: str = Field(alias="runId")
    agent: str
    task: str
    instruction: str

    model_config = ConfigDict(populate_by_name=True)


class TriageInput(BaseModel):
    thread_id: str = Field(alias="threadId")
    run_id: str = Field(alias="runId")
    title: str
    description: str

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "agui-agent-runner"}


@app.get("/agents")
async def agents() -> dict:
    return {"agents": dict(AGENTS), "tasks": dict(TASKS)}


@app.post("/agui")
async def agui_endpoint(body: AgentRunInput) -> StreamingResponse:
    """
    Stream AG-UI events for a single agent run.

    Accepts JSON with threadId, runId, agent, task, instruction.
    Returns a text/event-stream response where each SSE data frame is a
    JSON-encoded AG-UI BaseEvent.
    """

    async def event_stream():
        async for event in agent_run_events(
            body.agent,
            body.task,
            body.instruction,
            body.thread_id,
            body.run_id,
        ):
            yield encoder.encode(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/agui/triage")
async def agui_triage_endpoint(body: TriageInput) -> StreamingResponse:
    """
    Stream AG-UI events for the LangGraph triage proof of concept.

    This endpoint replaces the direct-LLM Phase 3 idea. The first version uses
    deterministic LangGraph nodes so the integration can be learned and tested
    without API keys.
    """

    async def event_stream():
        async for event in langgraph_triage_events(
            body.title,
            body.description,
            body.thread_id,
            body.run_id,
        ):
            yield encoder.encode(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Direct execution helper (not used by uvicorn, but handy for quick tests)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("agui_server:app", host="0.0.0.0", port=PORT, reload=True)
