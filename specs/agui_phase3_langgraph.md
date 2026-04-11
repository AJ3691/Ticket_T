# AG-UI Integration Spec - Phase 3: LangGraph Streaming Adapter
# Status: DRAFT - planning document

---

## Overview

Add a small LangGraph-based support ticket triage workflow and stream its
execution through the existing AG-UI frontend.

The goal is educational first:

1. Learn how LangGraph models state, nodes, and edges.
2. Learn how LangGraph streams graph execution.
3. Learn how an adapter translates LangGraph stream chunks into AG-UI events.

This phase should reuse the Phase 1/2 AG-UI infrastructure:

- `agui_server.py`
- `agent_runner/agui_adapter.py`
- `agui-frontend/`

The existing Claude CLI agent runner stays intact. LangGraph is added as a
second backend mode.

---

## Target Architecture

```text
React frontend
  |
  | POST /agui/triage
  v
agui_server.py
  |
  | calls langgraph_triage_events(...)
  v
agent_runner/langgraph_adapter.py
  |
  | emits AG-UI events
  | calls graph.astream(...)
  v
agent_runner/langgraph_triage.py
  |
  | compiled LangGraph workflow
  v
LangGraph nodes
  |
  | stream updates/messages/custom progress
  v
AG-UI SSE response
  |
  v
EventStream.tsx renders the run
```

---

## Design Principle

AG-UI is not the agent runtime. LangGraph is not the UI protocol.

This integration uses a thin adapter:

```text
LangGraph stream chunk -> AG-UI event
```

The frontend should not know whether events came from:

- Claude CLI through `agent_runner/agui_adapter.py`
- LangGraph through `agent_runner/langgraph_adapter.py`
- a future direct LLM API adapter

As long as the backend emits AG-UI events, the existing event renderer can show
the run.

---

## Files To Create

### 1. `agent_runner/langgraph_triage.py`

Purpose: define the learning-focused LangGraph workflow.

Suggested contents:

```python
from typing import TypedDict
from langgraph.graph import END, START, StateGraph


class TriageState(TypedDict):
    title: str
    description: str
    category: str
    recommendations: list[dict[str, object]]
    final_text: str


def build_triage_graph():
    graph = StateGraph(TriageState)
    graph.add_node("classify_ticket", classify_ticket)
    graph.add_node("draft_recommendations", draft_recommendations)
    graph.add_node("format_response", format_response)
    graph.add_edge(START, "classify_ticket")
    graph.add_edge("classify_ticket", "draft_recommendations")
    graph.add_edge("draft_recommendations", "format_response")
    graph.add_edge("format_response", END)
    return graph.compile()
```

Initial node behavior should be deterministic and local. Do not require an API
key in the first implementation.

Node responsibilities:

| Node | Purpose | Output |
|------|---------|--------|
| `classify_ticket` | Classify the ticket into a category from simple keywords | `category` |
| `draft_recommendations` | Generate 3 ranked recommendations from the category | `recommendations` |
| `format_response` | Convert recommendations into readable text | `final_text` |

Suggested categories:

- `account_access`
- `billing`
- `bug`
- `performance`
- `networking`
- `general`

Why deterministic first:

- It teaches LangGraph mechanics without model/API setup.
- It keeps tests fast and stable.
- It lets the AG-UI adapter be validated independently from LLM behavior.

Later enhancement:

- Replace `draft_recommendations` with an LLM node.
- Keep the adapter and endpoint unchanged.

---

### 2. `agent_runner/langgraph_adapter.py`

Purpose: convert LangGraph execution into AG-UI events.

Function signature:

```python
async def langgraph_triage_events(
    title: str,
    description: str,
    thread_id: str,
    run_id: str,
) -> AsyncGenerator[BaseEvent, None]:
```

Expected AG-UI event lifecycle:

```text
RunStartedEvent
StepStartedEvent("langgraph:triage")
TextMessageStartEvent
TextMessageContentEvent(s)
TextMessageEndEvent
StepFinishedEvent("langgraph:triage")
RunFinishedEvent
```

On error:

```text
RunStartedEvent
RunErrorEvent(code="LANGGRAPH_ERROR")
```

Suggested mapping:

| LangGraph signal | AG-UI event |
|------------------|-------------|
| graph starts | `RunStartedEvent` |
| adapter starts graph step | `StepStartedEvent("langgraph:triage")` |
| node update from `stream_mode="updates"` | `TextMessageContentEvent` with a compact state summary |
| model token from `stream_mode="messages"` | `TextMessageContentEvent` with token text |
| custom progress message | `TextMessageContentEvent` |
| graph completes | `RunFinishedEvent` |
| exception | `RunErrorEvent(code="LANGGRAPH_ERROR")` |

Initial implementation can use:

```python
async for chunk in graph.astream(input_state, stream_mode="updates"):
    ...
```

Later, when adding a real chat model node:

```python
async for mode, chunk in graph.astream(
    input_state,
    stream_mode=["updates", "messages", "custom"],
):
    ...
```

The adapter should keep the frontend payload generic. Avoid exposing internal
LangGraph objects directly. Convert chunks to short readable strings.

---

### 3. `tests/test_agui_langgraph.py`

Purpose: verify the graph and adapter without real LLM calls.

Test cases:

```text
test_langgraph_graph_returns_final_text
test_langgraph_graph_is_deterministic
test_langgraph_adapter_emits_run_started
test_langgraph_adapter_emits_text_content
test_langgraph_adapter_event_sequence
test_langgraph_adapter_error
test_langgraph_endpoint_returns_sse
test_langgraph_endpoint_contains_run_finished
```

Testing rules:

- No real network calls.
- No real LLM calls.
- Tests must pass without API keys.
- Use deterministic graph behavior for assertions.

---

## Files To Update

### 1. `agui_server.py`

Add endpoint:

```text
POST /agui/triage
```

Request model:

```python
class LangGraphTriageInput(BaseModel):
    thread_id: str = Field(alias="threadId")
    run_id: str = Field(alias="runId")
    title: str
    description: str

    model_config = ConfigDict(populate_by_name=True)
```

Handler:

```python
@app.post("/agui/triage")
async def langgraph_triage_endpoint(body: LangGraphTriageInput):
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
```

Do not change the existing `/agui` endpoint.

---

### 2. `agui-frontend/src/types.ts`

Add a run mode:

```typescript
export type RunMode = "agent" | "langgraph";
```

Add request shape:

```typescript
export interface LangGraphTriageRequest {
  title: string;
  description: string;
  threadId: string;
  runId: string;
}
```

---

### 3. `agui-frontend/src/hooks/useAgentRun.ts`

Either:

1. Rename to `useAguiRun.ts`, or
2. Keep the name and add a second function:

```typescript
runLangGraphTriage(request: LangGraphTriageRequest)
```

Both functions should share the same SSE parser.

Preferred shape:

```typescript
function streamEvents(path: string, body: object): Promise<void>
```

Then:

```typescript
runAgent(...) -> streamEvents("/agui", request)
runLangGraphTriage(...) -> streamEvents("/agui/triage", request)
```

---

### 4. `agui-frontend/src/App.tsx`

Add mode state:

```typescript
const [mode, setMode] = useState<RunMode>("agent");
```

Render:

```text
Agent Runner | LangGraph Triage
```

In Agent Runner mode:

- existing agent/task/instruction form

In LangGraph Triage mode:

- title input
- description textarea
- run button

The existing `EventStream` component should remain generic and unchanged if
possible.

---

### 5. `requirements.txt`

Add:

```text
langgraph>=0.2
```

If adding a real LLM node in this phase, also add the provider integration, for
example:

```text
langchain-anthropic>=0.2
```

Recommendation: start without the provider dependency, then add it in a later
iteration.

---

### 6. `docs/agui.md`

Append a Phase 3 section:

- What was built
- How LangGraph state/nodes/edges work
- How LangGraph stream chunks map to AG-UI events
- How to run backend/frontend
- How to test the LangGraph endpoint

---

## API Contract

Endpoint:

```text
POST /agui/triage
```

Request:

```json
{
  "threadId": "thread-1",
  "runId": "run-1",
  "title": "Cannot log in",
  "description": "Password reset token says expired"
}
```

Response:

```text
Content-Type: text/event-stream
```

Example event flow:

```text
data: {"type":"RUN_STARTED","threadId":"thread-1","runId":"run-1"}

data: {"type":"STEP_STARTED","stepName":"langgraph:triage"}

data: {"type":"TEXT_MESSAGE_START","messageId":"abc123","role":"assistant"}

data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"abc123","delta":"[classify_ticket] category: account_access"}

data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"abc123","delta":"1. Reset password and verify login session..."}

data: {"type":"TEXT_MESSAGE_END","messageId":"abc123"}

data: {"type":"STEP_FINISHED","stepName":"langgraph:triage"}

data: {"type":"RUN_FINISHED","threadId":"thread-1","runId":"run-1"}
```

---

## Implementation Phases

### Phase 3A - Deterministic LangGraph

Build the graph with local deterministic nodes.

Done when:

- `agent_runner/langgraph_triage.py` exists.
- `agent_runner/langgraph_adapter.py` exists.
- `/agui/triage` streams events.
- Frontend has a LangGraph mode.
- Tests pass without API keys.

### Phase 3B - Optional LLM Node

Replace or extend `draft_recommendations` with a chat model call.

Done when:

- LLM text streams through LangGraph.
- Missing API key returns a useful `RUN_ERROR`.
- Tests still mock the LLM.

### Phase 3C - Optional Structured Tool Events

Map structured recommendation output to AG-UI tool call events.

Potential events:

- `ToolCallStartEvent`
- `ToolCallArgsEvent`
- `ToolCallEndEvent`

This is optional. It should only be added after text streaming works.

---

## Verification Commands

```powershell
# Backend imports
python -c "from agent_runner.langgraph_triage import build_triage_graph; print('OK: graph imports')"
python -c "from agent_runner.langgraph_adapter import langgraph_triage_events; print('OK: adapter imports')"
python -c "from agui_server import app; print('OK: server imports')"

# Backend tests
python -m pytest tests/test_agui_langgraph.py -v
python -m pytest -v

# Frontend build
cd agui-frontend
npm.cmd run build
```

Manual smoke test:

```powershell
uvicorn agui_server:app --reload --port 8002
```

Then:

```powershell
curl -N -X POST http://localhost:8002/agui/triage `
  -H "Content-Type: application/json" `
  -d "{\"threadId\":\"t1\",\"runId\":\"r1\",\"title\":\"Cannot log in\",\"description\":\"Password reset token expired\"}"
```

Expected:

```text
RUN_STARTED
STEP_STARTED
TEXT_MESSAGE_START
TEXT_MESSAGE_CONTENT
TEXT_MESSAGE_END
STEP_FINISHED
RUN_FINISHED
```

Frontend smoke test:

```powershell
cd agui-frontend
npm.cmd run dev
```

Open:

```text
http://localhost:5173
```

Select:

```text
LangGraph Triage
```

Enter a title and description. The output panel should stream graph progress
and final recommendations.

---

## Acceptance Criteria

- [ ] LangGraph dependency added.
- [ ] Deterministic triage graph compiles.
- [ ] Graph has at least three nodes: classify, draft, format.
- [ ] Adapter emits valid AG-UI lifecycle events.
- [ ] `/agui/triage` returns `text/event-stream`.
- [ ] Frontend can switch between Agent Runner and LangGraph Triage.
- [ ] Existing Agent Runner mode still works.
- [ ] Existing `EventStream` renders both modes.
- [ ] Tests pass without API keys.
- [ ] `npm.cmd run build` passes.
- [ ] Documentation explains how LangGraph maps to AG-UI.

---

## Out Of Scope

- No persistence/checkpointer in first implementation.
- No multi-agent LangGraph flow yet.
- No authentication.
- No production deployment changes.
- No direct write-back to ticket systems.
- No forced LLM dependency in tests.

---

## Open Questions

1. The first implementation is deterministic for a simple proof of concept.
   An LLM-backed node is optional and should be added after the integration is
   understandable.
2. The LangGraph proof of concept replaces the earlier direct-LLM endpoint and
   uses `POST /agui/triage`.
3. LangGraph updates render as plain AG-UI text content first. Structured rows
   can be added later.
4. The graph stays separate from the existing `app.engine.get_recommendations`
   for now so the LangGraph integration is easy to understand.
