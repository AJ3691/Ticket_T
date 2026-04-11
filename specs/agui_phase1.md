# AG-UI Integration Spec — Phase 1: Wire Backend
# Status: APPROVED — ready for implementation

---

## Overview

Add an AG-UI SSE endpoint to the existing agent runner so Claude CLI agent
executions emit structured AG-UI events over HTTP. Verify with curl.
No frontend in this phase.

---

## What exists today (read-only context — do not modify these files)

| File | Role |
|------|------|
| `agent_runner/registry.py` | Maps agent names → `.md` files, task names → `.md` files |
| `agent_runner/executor.py` | `build_prompt()`, `run_captured()` with `line_callback`, `_stream_subprocess()` |
| `agent_runner/parallel.py` | `AgentJob` dataclass, `run_parallel()` |
| `agent_runner/cli.py` | Typer CLI — `agent run`, `agent list` |
| `app/main.py` | FastAPI app for the ticket triage API (separate from this work) |

### Key interfaces to reuse

```python
from agent_runner.executor import build_prompt, run_captured
# run_captured(agent, task, instruction, project_dir, *, timeout=300, line_callback=None)
# → tuple[int, str]  (exit_code, full_output)
# Calls line_callback(line) for each line of subprocess output

from agent_runner.registry import resolve_agent, resolve_task, AGENTS, TASKS
# resolve_agent("core") → "agents/agent_core.md" or raises ValueError
# resolve_task("add_strategy") → "prompts/add_strategy.md" or raises ValueError
```

---

## Files to create

### 1. `agent_runner/agui_adapter.py`

**Purpose:** Async generator that translates subprocess execution → AG-UI events.

**Function signature:**
```python
async def agent_run_events(
    agent: str,
    task: str,
    instruction: str,
    thread_id: str,
    run_id: str,
) -> AsyncGenerator[BaseEvent, None]:
```

**Internal flow:**

1. Validate agent/task with `resolve_agent()` / `resolve_task()`
   - On `ValueError`: yield `RunStartedEvent` → `RunErrorEvent(code="INVALID_AGENT")` → return
2. Yield `RunStartedEvent(thread_id=thread_id, run_id=run_id)`
3. Yield `StepStartedEvent(step_name=f"{agent}:{task}")`
4. Generate `message_id = uuid4().hex[:12]`
5. Yield `TextMessageStartEvent(message_id=message_id, role="assistant")`
6. Run subprocess in a background thread:
   - Create a `queue.Queue()`
   - Launch `threading.Thread` that calls `run_captured(agent, task, instruction, project_dir, line_callback=queue.put)`
   - Store exit code in a mutable container (e.g. list) so the async side can read it
7. Poll loop:
   ```python
   while thread.is_alive() or not q.empty():
       try:
           line = q.get_nowait()
           stripped = line.rstrip("\n")
           if stripped:
               yield TextMessageContentEvent(message_id=message_id, delta=stripped)
       except queue.Empty:
           pass
       await asyncio.sleep(0.05)
   ```
8. After loop exits, drain any remaining items from queue
9. Yield `TextMessageEndEvent(message_id=message_id)`
10. Yield `StepFinishedEvent(step_name=f"{agent}:{task}")`
11. If exit_code == 0: yield `RunFinishedEvent(thread_id=thread_id, run_id=run_id)`
12. If exit_code != 0: yield `RunErrorEvent(message=f"Agent '{agent}' failed (exit {exit_code})", code=str(exit_code))`

**Imports needed:**
```python
import asyncio
import queue
import threading
from pathlib import Path
from uuid import uuid4
from ag_ui.core import (
    EventType, RunStartedEvent, RunFinishedEvent, RunErrorEvent,
    StepStartedEvent, StepFinishedEvent,
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
)
from agent_runner.executor import run_captured
from agent_runner.registry import resolve_agent, resolve_task
```

**PROJECT_DIR:** `Path(__file__).parent.parent.resolve()`

---

### 2. `agui_server.py` (project root)

**Purpose:** FastAPI app exposing AG-UI SSE endpoint for the agent runner.

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Returns `{"status": "ok", "service": "agui-agent-runner"}` |
| `GET` | `/agents` | Returns `{"agents": {...}, "tasks": {...}}` from registry |
| `POST` | `/agui` | Accepts agent run input, returns SSE stream of AG-UI events |

**POST /agui input model:**
```python
class AgentRunInput(BaseModel):
    thread_id: str = Field(alias="threadId")
    run_id: str = Field(alias="runId")
    agent: str
    task: str
    instruction: str

    model_config = ConfigDict(populate_by_name=True)
```

**POST /agui handler:**
```python
from starlette.responses import StreamingResponse
from ag_ui.encoder import EventEncoder
from agent_runner.agui_adapter import agent_run_events

encoder = EventEncoder()

@app.post("/agui")
async def agui_endpoint(body: AgentRunInput):
    async def event_stream():
        async for event in agent_run_events(
            body.agent, body.task, body.instruction,
            body.thread_id, body.run_id,
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
```

**CORS middleware:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 3. `tests/test_agui_phase1.py`

**Purpose:** Automated tests for the AG-UI adapter and server.

**Test cases:**

```python
# --- Adapter tests (unit) ---

# test_adapter_valid_agent_emits_run_started
# Call agent_run_events with a valid agent/task but mock run_captured
# to return immediately. First event should be RunStartedEvent.

# test_adapter_invalid_agent_emits_error
# Call agent_run_events with agent="nonexistent".
# Should yield RunStartedEvent then RunErrorEvent with code="INVALID_AGENT".

# test_adapter_invalid_task_emits_error
# Call agent_run_events with task="nonexistent".
# Should yield RunStartedEvent then RunErrorEvent with code="INVALID_TASK".

# test_adapter_event_sequence
# Mock run_captured to emit 3 lines via line_callback.
# Collect all events. Verify sequence:
#   RunStartedEvent → StepStartedEvent → TextMessageStartEvent →
#   3x TextMessageContentEvent → TextMessageEndEvent →
#   StepFinishedEvent → RunFinishedEvent

# test_adapter_failed_agent_emits_run_error
# Mock run_captured to return exit_code=1.
# Last event should be RunErrorEvent, not RunFinishedEvent.

# test_adapter_message_id_consistent
# All TextMessage events for one run share the same message_id.

# --- Server tests (integration) ---

# test_health_endpoint
# GET /health → 200, body matches expected JSON.

# test_agents_endpoint
# GET /agents → 200, response contains "agents" and "tasks" keys.

# test_agui_endpoint_returns_sse
# POST /agui with valid input (mocked executor).
# Response content-type is text/event-stream.
# Body contains "RUN_STARTED" and "RUN_FINISHED".

# test_agui_endpoint_invalid_agent
# POST /agui with agent="bogus".
# Response contains RUN_ERROR event.

# test_agui_cors_headers
# OPTIONS /agui should return CORS headers.
```

**Testing approach:**
- Mock `run_captured` using `unittest.mock.patch` to avoid actually invoking Claude CLI
- The mock should accept `line_callback` and call it with a few test lines
- Use `httpx.AsyncClient` with `app` for server tests
- Parse SSE lines from response body to verify event types

---

### 4. Update `requirements.txt`

Append:
```
ag-ui-protocol>=0.1.14
```

---

### 5. Update `docs/agui.md` (create if not exists)

After implementation, create this file with:
- What was built (file list)
- How to run the AG-UI server
- Architecture: adapter pattern, threading model, SSE encoding
- curl examples for testing
- Pointer to Phase 2 spec

---

## How to run

```bash
# Install new dependency
pip install ag-ui-protocol>=0.1.14

# Start AG-UI server (port 8001 to avoid conflict with triage API on 8000)
uvicorn agui_server:app --reload --port 8001
```

---

## Verification commands (all must pass)

```bash
# 1. Import checks
python -c "from agent_runner.agui_adapter import agent_run_events; print('OK: adapter imports')"
python -c "from agui_server import app; print('OK: server imports')"

# 2. Automated tests
pytest tests/test_agui_phase1.py -v

# 3. Manual smoke tests (start server first)
# Health
curl -s http://localhost:8001/health | python -m json.tool
# Expected: {"status": "ok", "service": "agui-agent-runner"}

# Agent registry
curl -s http://localhost:8001/agents | python -m json.tool
# Expected: {"agents": {"schema": "agents/agent_schema.md", ...}, "tasks": {...}}

# SSE stream (requires Claude CLI — skip if not available)
curl -N -X POST http://localhost:8001/agui \
  -H "Content-Type: application/json" \
  -d '{"threadId":"t1","runId":"r1","agent":"core","task":"add_strategy","instruction":"Add networking"}'
# Expected: SSE events starting with RUN_STARTED, ending with RUN_FINISHED
```

---

## Acceptance criteria

- [ ] `uvicorn agui_server:app --port 8001` starts without errors
- [ ] `GET /health` returns `{"status": "ok", "service": "agui-agent-runner"}`
- [ ] `GET /agents` returns agent and task registries as JSON
- [ ] `POST /agui` with valid input returns `text/event-stream` response
- [ ] First SSE event is `RUN_STARTED` with matching threadId/runId
- [ ] Last SSE event is `RUN_FINISHED` (success) or `RUN_ERROR` (failure)
- [ ] Each subprocess output line becomes a `TEXT_MESSAGE_CONTENT` event
- [ ] `TEXT_MESSAGE_START` and `TEXT_MESSAGE_END` bracket the content events
- [ ] `STEP_STARTED` and `STEP_FINISHED` bracket the agent execution
- [ ] Invalid agent → `RUN_ERROR` with code `INVALID_AGENT`
- [ ] Invalid task → `RUN_ERROR` with code `INVALID_TASK`
- [ ] Events are valid SSE format: `data: {json}\n\n`
- [ ] CORS headers present on responses
- [ ] `pytest tests/test_agui_phase1.py -v` — all tests pass
- [ ] `docs/agui.md` created with Phase 1 documentation
- [ ] No modifications to existing files except `requirements.txt`

---

## Out of scope

- No frontend (Phase 2)
- No parallel agent runs through AG-UI
- No direct LLM calls (Phase 3)
- No authentication or persistence
- No changes to existing CLI or MCP server

---

## Context for the implementing agent

**Working directory:** Project root (where `AGENTS.md` lives)

**Read first:**
1. `agent_runner/executor.py` — understand `run_captured()` and `_stream_subprocess()`
2. `agent_runner/registry.py` — understand AGENTS/TASKS dicts and resolve functions
3. `requirements.txt` — current dependencies

**Create:**
1. `agent_runner/agui_adapter.py`
2. `agui_server.py`
3. `tests/test_agui_phase1.py`
4. `docs/agui.md`

**Update:**
1. `requirements.txt` — append `ag-ui-protocol>=0.1.14`

**Verify:** Run every command in the "Verification commands" section. Report results.
