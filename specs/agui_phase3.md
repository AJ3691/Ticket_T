# AG-UI Integration Spec — Phase 3: Direct LLM Streaming Service
# Status: APPROVED — ready for implementation (after Phase 2 verified)
# Prerequisite: Phase 1 + Phase 2 complete and working

---

## Overview

Add a second AG-UI service that calls an LLM directly (Anthropic Claude API)
instead of shelling out to the Claude CLI. This proves the AG-UI protocol
works with multiple backend types through the same frontend — the production
pattern.

The user picks "LLM Triage" mode in the frontend, types a support ticket, and
watches the LLM reason through recommendations in real time — with tool calls
visible as structured events.

---

## What exists from Phase 1 + 2 (do not modify)

| Component | Role |
|-----------|------|
| `agui_server.py` | FastAPI with `POST /agui` for CLI agent runs |
| `agent_runner/agui_adapter.py` | CLI subprocess → AG-UI events |
| `agui-frontend/` | React app rendering AG-UI SSE streams |

---

## What to build

### 1. `agent_runner/llm_adapter.py`

**Purpose:** Async generator that calls the Anthropic API directly and yields
AG-UI events as the response streams in.

**Function signature:**
```python
async def llm_triage_events(
    title: str,
    description: str,
    thread_id: str,
    run_id: str,
) -> AsyncGenerator[BaseEvent, None]:
```

**Internal flow:**

1. Yield `RunStartedEvent(thread_id, run_id)`
2. Yield `StepStartedEvent(step_name="llm:triage")`
3. Generate `message_id = uuid4().hex[:12]`
4. Yield `TextMessageStartEvent(message_id=message_id, role="assistant")`
5. Call Anthropic API with streaming:
   ```python
   import anthropic
   client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var
   
   with client.messages.stream(
       model="claude-sonnet-4-20250514",
       max_tokens=1024,
       system="You are a support ticket triage assistant. Analyze the ticket and provide ranked recommendations. For each recommendation provide: action, confidence (0-1), and why (1-2 sentences).",
       messages=[{
           "role": "user",
           "content": f"Title: {title}\nDescription: {description}\n\nProvide 3 ranked recommendations."
       }],
   ) as stream:
       for text in stream.text_stream:
           yield TextMessageContentEvent(message_id=message_id, delta=text)
   ```
6. Yield `TextMessageEndEvent(message_id=message_id)`
7. Yield `StepFinishedEvent(step_name="llm:triage")`
8. Yield `RunFinishedEvent(thread_id=thread_id, run_id=run_id)`

**Error handling:**
- If `ANTHROPIC_API_KEY` not set: yield `RunErrorEvent(message="ANTHROPIC_API_KEY not set", code="MISSING_API_KEY")`
- If API call fails: yield `RunErrorEvent(message=str(error), code="LLM_ERROR")`
- Always emit `RunStartedEvent` before any error event

**Optional enhancement — tool use:**
If time permits, define a tool for structured output:
```python
tools = [{
    "name": "provide_recommendations",
    "description": "Provide ranked triage recommendations",
    "input_schema": {
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "confidence": {"type": "number"},
                        "why": {"type": "string"}
                    }
                }
            }
        }
    }
}]
```

When tool use is detected:
- Yield `ToolCallStartEvent(tool_call_id=..., tool_call_name="provide_recommendations")`
- Yield `ToolCallArgsEvent(tool_call_id=..., delta=json_chunk)` for each chunk
- Yield `ToolCallEndEvent(tool_call_id=...)`

This shows the frontend rendering tool calls as structured data alongside text.

---

### 2. Update `agui_server.py` — add new endpoint

**New endpoint:** `POST /agui/triage`

```python
class TriageInput(BaseModel):
    thread_id: str = Field(alias="threadId")
    run_id: str = Field(alias="runId")
    title: str
    description: str

    model_config = ConfigDict(populate_by_name=True)

@app.post("/agui/triage")
async def agui_triage_endpoint(body: TriageInput):
    async def event_stream():
        async for event in llm_triage_events(
            body.title, body.description,
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

---

### 3. Update `agui-frontend/` — add triage mode

**Changes to frontend:**

- **Add a mode toggle** at the top of the form: "Agent Runner" | "LLM Triage"
- **Agent Runner mode** (existing): agent dropdown, task dropdown, instruction input → POST /agui
- **LLM Triage mode** (new): title input, description textarea → POST /agui/triage
- **EventStream component** unchanged — it already renders AG-UI events generically
- **If tool call events arrive**: render them as a structured card showing the recommendation JSON

The point is: **same rendering pipeline, different backend**. This is the AG-UI value prop.

---

### 4. `tests/test_agui_phase3.py`

**Test cases:**

```python
# --- LLM adapter tests (unit, mocked API) ---

# test_llm_adapter_emits_run_started
# Mock anthropic client. First event should be RunStartedEvent.

# test_llm_adapter_streams_text_content
# Mock streaming response with 3 text chunks.
# Should yield 3 TextMessageContentEvent with correct deltas.

# test_llm_adapter_event_sequence
# Full mock run. Verify:
#   RunStartedEvent → StepStartedEvent → TextMessageStartEvent →
#   TextMessageContentEvent(s) → TextMessageEndEvent →
#   StepFinishedEvent → RunFinishedEvent

# test_llm_adapter_missing_api_key
# Unset ANTHROPIC_API_KEY. Should yield RunErrorEvent with code="MISSING_API_KEY".

# test_llm_adapter_api_error
# Mock API to raise an exception.
# Should yield RunErrorEvent with code="LLM_ERROR".

# --- Server tests (integration) ---

# test_triage_endpoint_returns_sse
# POST /agui/triage with valid input (mocked LLM).
# Response content-type is text/event-stream.

# test_triage_endpoint_contains_events
# Parse SSE body. Must contain RUN_STARTED and RUN_FINISHED.
```

**Mocking strategy:**
- Mock `anthropic.Anthropic` to avoid real API calls in tests
- Create a fake streaming context manager that yields test text chunks
- Tests must pass without `ANTHROPIC_API_KEY` set

---

### 5. Update `requirements.txt`

Append:
```
anthropic>=0.52
```

---

### 6. Update `docs/agui.md`

Append Phase 3 section with:
- What was built
- The two-backend architecture diagram
- How to set `ANTHROPIC_API_KEY`
- How to test both modes
- Architecture decision: why direct API vs CLI for this use case

---

## How to run

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."   # Linux/Mac
# or
$env:ANTHROPIC_API_KEY="sk-ant-..."     # PowerShell

# Backend
uvicorn agui_server:app --reload --port 8001

# Frontend
cd agui-frontend && npm run dev

# Test LLM triage with curl
curl -N -X POST http://localhost:8001/agui/triage \
  -H "Content-Type: application/json" \
  -d '{
    "threadId": "t1",
    "runId": "r1",
    "title": "Cannot log in",
    "description": "I reset my password but still get an error"
  }'
```

---

## Verification commands

```bash
# 1. Import check
python -c "from agent_runner.llm_adapter import llm_triage_events; print('OK: llm adapter imports')"

# 2. Automated tests (no API key needed — all mocked)
pytest tests/test_agui_phase3.py -v

# 3. Full test suite still passes
pytest -v

# 4. Manual smoke test (requires ANTHROPIC_API_KEY)
# Start server, then:
curl -N -X POST http://localhost:8001/agui/triage \
  -H "Content-Type: application/json" \
  -d '{"threadId":"t1","runId":"r1","title":"Cannot log in","description":"Password reset error"}'
# Expected: streaming SSE with LLM-generated triage recommendations

# 5. Frontend check
# Open http://localhost:5173
# Toggle to "LLM Triage" mode
# Enter title + description, click Run
# Watch LLM response stream in real time
```

---

## Acceptance criteria

- [ ] `from agent_runner.llm_adapter import llm_triage_events` imports without error
- [ ] `POST /agui/triage` returns SSE stream with AG-UI events
- [ ] LLM response text streams as `TEXT_MESSAGE_CONTENT` events
- [ ] Missing API key → `RUN_ERROR` with code `MISSING_API_KEY`
- [ ] API failure → `RUN_ERROR` with code `LLM_ERROR`
- [ ] `pytest tests/test_agui_phase3.py -v` — all tests pass (mocked, no API key needed)
- [ ] `pytest -v` — full suite still passes (no regressions)
- [ ] Frontend shows mode toggle: "Agent Runner" | "LLM Triage"
- [ ] LLM Triage mode shows title + description inputs
- [ ] LLM response streams in real time in the event panel
- [ ] Same `EventStream` component renders both modes
- [ ] `requirements.txt` updated with `anthropic>=0.52`
- [ ] `docs/agui.md` updated with Phase 3 section
- [ ] No modifications to Phase 1 adapter or Phase 1 tests

---

## Out of scope

- No tool use visualization (optional enhancement noted above)
- No conversation history
- No model selection UI
- No cost tracking
- No caching of LLM responses

---

## Context for the implementing agent

**Working directory:** Project root

**Prerequisite check:**
```bash
# Phase 1 backend running
curl -s http://localhost:8001/health

# Phase 2 frontend running
# Open http://localhost:5173 — app loads
```

**Read first:**
1. `agent_runner/agui_adapter.py` — follow the same pattern for the LLM adapter
2. `agui_server.py` — understand existing endpoint structure
3. `agui-frontend/src/hooks/useAgentRun.ts` — understand SSE parsing
4. `agui-frontend/src/components/AgentForm.tsx` — understand form structure

**Create:**
1. `agent_runner/llm_adapter.py`
2. `tests/test_agui_phase3.py`

**Update:**
1. `agui_server.py` — add `POST /agui/triage` endpoint
2. `agui-frontend/src/App.tsx` — add mode toggle
3. `agui-frontend/src/components/AgentForm.tsx` — add triage form fields
4. `agui-frontend/src/api.ts` — add triage API call
5. `requirements.txt` — append `anthropic>=0.52`
6. `docs/agui.md` — append Phase 3 section
