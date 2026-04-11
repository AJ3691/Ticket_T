# AG-UI Integration Log

---

## Phase 1 — Wire AG-UI Backend

### What was built

| File | Action | Purpose |
|------|--------|---------|
| `agent_runner/agui_adapter.py` | Created | Async generator: subprocess execution → AG-UI events |
| `agui_server.py` | Created | FastAPI app with `/health`, `/agents`, `/agui` (SSE) endpoints |
| `tests/test_agui_phase1.py` | Created | 11 unit + integration tests for adapter and server |
| `requirements.txt` | Updated | Added `ag-ui-protocol>=0.1.14` |
| `docs/agui.md` | Created | This file |

---

### How to run

```bash
# Install dependencies (ag-ui SDK is in the repo)
pip install -e ./ag-ui/sdks/python
pip install -r requirements.txt

# Start the AG-UI server (port configurable via env var, default 8002)
AGUI_PORT=8002 uvicorn agui_server:app --reload --port 8002
```

---

### Smoke tests (server must be running)

```bash
# Health check
curl -s http://localhost:8002/health | python -m json.tool
# Expected: {"status": "ok", "service": "agui-agent-runner"}

# Agent + task registry
curl -s http://localhost:8002/agents | python -m json.tool
# Expected: {"agents": {"schema": "...", "api": "...", ...}, "tasks": {...}}

# SSE stream — requires Claude CLI to be installed and authenticated
curl -N -X POST http://localhost:8002/agui \
  -H "Content-Type: application/json" \
  -d '{"threadId":"t1","runId":"r1","agent":"core","task":"add_strategy","instruction":"Add networking"}'
# Expected: SSE events starting with RUN_STARTED, ending with RUN_FINISHED or RUN_ERROR
```

---

### Architecture decisions

**Adapter pattern — threading + asyncio queue bridge**

`run_captured()` in `executor.py` is synchronous and calls a `line_callback` for each output line from the Claude CLI subprocess. The AG-UI endpoint is async (FastAPI + Starlette streaming). To bridge these two worlds without rewriting the executor:

- A background `threading.Thread` runs `run_captured()` and puts each line into a `queue.Queue`.
- The async generator polls the queue with `await asyncio.sleep(0.05)` so the event loop stays free.
- Once the thread finishes, a final drain loop catches any lines queued after the `thread.is_alive()` check returned False.

This avoids blocking the event loop while keeping the existing executor interface intact. The 50ms poll interval is a reasonable tradeoff between responsiveness and CPU overhead.

**Event sequence**

Every run emits this wrapper sequence regardless of content:
```
RunStarted → StepStarted → TextMessageStart → [content events] → TextMessageEnd → StepFinished → RunFinished|RunError
```

Invalid agent/task names short-circuit immediately after `RunStarted` with a `RunErrorEvent` so the client always gets a `RunStarted` to latch onto.

**Port via env var**

`AGUI_PORT` (default `8002`) keeps the port out of code. The triage API runs on `8000`; `8002` avoids the common `8001` alternative as well.

**SSE encoding**

`EventEncoder` from `ag_ui.encoder` serialises each `BaseEvent` as:
```
data: {json}\n\n
```
`model_dump_json(by_alias=True, exclude_none=True)` is used so field names match the AG-UI protocol spec (camelCase aliases) and optional null fields are omitted.

---

### What's next

Phase 2 (`specs/agui_phase2.md`) builds a minimal React frontend that connects to this SSE endpoint and renders the agent output stream in a browser UI.

---

## Phase 2 - React Frontend

### What was built

| File | Action | Purpose |
|------|--------|---------|
| `agui-frontend/package.json` | Created | Vite + React + TypeScript project manifest |
| `agui-frontend/vite.config.ts` | Created | Vite dev server config on port 5173 |
| `agui-frontend/tsconfig.json` | Created | Strict TypeScript config |
| `agui-frontend/index.html` | Created | Browser entry document |
| `agui-frontend/src/main.tsx` | Created | React render entry point |
| `agui-frontend/src/App.tsx` | Created | Main layout, registry load, run orchestration |
| `agui-frontend/src/api.ts` | Created | Backend registry fetch helper |
| `agui-frontend/src/types.ts` | Created | Minimal AG-UI event type definitions |
| `agui-frontend/src/hooks/useAgentRun.ts` | Created | POST `/agui`, parse SSE stream, track run state |
| `agui-frontend/src/components/AgentForm.tsx` | Created | Agent/task/instruction form |
| `agui-frontend/src/components/EventStream.tsx` | Created | Live event output renderer with auto-scroll |
| `agui-frontend/src/components/StatusBadge.tsx` | Created | Idle/running/done/error state indicator |
| `agui-frontend/src/styles.css` | Created | Minimal dark UI styling |
| `agui-frontend/README.md` | Created | Frontend setup and usage notes |

### How to run

```powershell
# Terminal 1 - backend
uvicorn agui_server:app --reload --port 8002

# Terminal 2 - frontend
cd agui-frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The frontend defaults to `http://localhost:8002`, matching the current Phase 1 backend docs. To point it at another backend port:

```powershell
$env:VITE_AGUI_BASE_URL="http://localhost:8001"
npm run dev
```

### Architecture decisions

**Standalone app**

The frontend lives in `agui-frontend/` as a separate Vite app. It does not live under the triage API package and does not modify Phase 1 Python files.

**Manual SSE parsing**

The browser client uses `fetch()` with `ReadableStream` and parses `data: ...\n\n` frames directly. This keeps the frontend dependency set small and mirrors the AG-UI event stream produced by `EventEncoder`.

**Runtime backend URL**

`VITE_AGUI_BASE_URL` controls the backend URL. The default is `http://localhost:8002` because Phase 1 currently documents and configures the AG-UI server on that port.

### What's next

Phase 3 can follow either the direct LLM plan in `specs/agui_phase3.md` or the LangGraph-focused learning plan in `specs/agui_phase3_langgraph.md`. The LangGraph plan keeps the same AG-UI event pipeline while adding a graph-based triage workflow.
