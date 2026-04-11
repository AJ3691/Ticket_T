# AG-UI Integration Spec — Phase 2: React Frontend
# Status: APPROVED — ready for implementation (after Phase 1 verified)
# Prerequisite: Phase 1 complete — `agui_server.py` running on port 8001

---

## Overview

Build a minimal React frontend that connects to the AG-UI backend from Phase 1
and renders agent executions in real time. The goal is a functional UI, not a
polished product — prove the end-to-end flow works in a browser.

---

## What exists from Phase 1 (do not modify)

| File | Role |
|------|------|
| `agui_server.py` | FastAPI app with `POST /agui`, `GET /health`, `GET /agents` |
| `agent_runner/agui_adapter.py` | Async generator yielding AG-UI events |
| `tests/test_agui_phase1.py` | Backend tests |

### Backend API contract

```
GET  /health  → {"status": "ok", "service": "agui-agent-runner"}
GET  /agents  → {"agents": {"schema": "...", ...}, "tasks": {"add_strategy": "...", ...}}
POST /agui    → SSE stream of AG-UI events
     Body: {"threadId": "...", "runId": "...", "agent": "...", "task": "...", "instruction": "..."}
```

---

## What to build

### Directory: `agui-frontend/`

A standalone React app (Vite + React + TypeScript) in a subdirectory of the project.

**Do NOT put this inside `app/` — it's a separate application.**

### Project structure

```
agui-frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── main.tsx           — React entry point
│   ├── App.tsx            — Main layout: form + output panel
│   ├── components/
│   │   ├── AgentForm.tsx  — Agent/task/instruction selector + Run button
│   │   ├── EventStream.tsx — Renders streamed AG-UI events
│   │   └── StatusBadge.tsx — Shows idle/running/done/error state
│   ├── hooks/
│   │   └── useAgentRun.ts — Custom hook: manages SSE connection + event parsing
│   ├── types.ts           — AG-UI event type definitions (subset)
│   └── api.ts             — fetch /agents, POST /agui
└── README.md
```

### UI Layout

```
┌─────────────────────────────────────────────────┐
│  Agent Runner — AG-UI                           │
├─────────────────────────────────────────────────┤
│                                                 │
│  Agent: [dropdown ▼]    Task: [dropdown ▼]      │
│  Instruction: [text input________________]      │
│  [Run Agent]                    [● idle]         │
│                                                 │
├─────────────────────────────────────────────────┤
│  Output                                         │
│  ─────────────────────────────────────────────  │
│  [RUN_STARTED] thread: t1, run: r1              │
│  [STEP_STARTED] core:add_strategy               │
│  Reading agents/agent_core.md...                │
│  Modifying keyword.py...                        │
│  Adding networking category...                  │
│  [STEP_FINISHED] core:add_strategy              │
│  [RUN_FINISHED] ✓                               │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Component Specifications

#### `App.tsx`
- Fetches agent/task list from `GET /agents` on mount
- Passes data to `AgentForm`
- Manages run state: idle → running → done/error
- Renders `AgentForm` + `EventStream` + `StatusBadge`

#### `AgentForm.tsx`
- Two dropdowns populated from `/agents` response
- Text input for instruction
- "Run Agent" button — disabled while running
- On submit: generates `threadId` + `runId` (uuid), calls the hook

#### `useAgentRun.ts` (custom hook)
- Accepts: `{ agent, task, instruction, threadId, runId }`
- Opens a `fetch()` to `POST /agui` with the body
- Reads the response as a `ReadableStream`
- Parses SSE lines (`data: {...}\n\n`) into typed event objects
- Maintains state:
  - `events: AgUIEvent[]` — all received events
  - `status: "idle" | "running" | "done" | "error"`
  - `textContent: string` — accumulated text from `TEXT_MESSAGE_CONTENT` deltas
- Returns `{ events, status, textContent, runAgent }`

**SSE parsing approach:**
```typescript
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  
  // Split on double newline (SSE boundary)
  const parts = buffer.split("\n\n");
  buffer = parts.pop() || "";
  
  for (const part of parts) {
    if (part.startsWith("data: ")) {
      const json = JSON.parse(part.slice(6));
      // dispatch event based on json.type
    }
  }
}
```

#### `EventStream.tsx`
- Renders the `events` array from the hook
- Each event displayed as a line with visual distinction:
  - `RUN_STARTED` / `RUN_FINISHED` → bold, with ✓ or ✗ icon
  - `STEP_STARTED` / `STEP_FINISHED` → indented, muted color
  - `TEXT_MESSAGE_CONTENT` → monospace, no prefix (the actual agent output)
  - `RUN_ERROR` → red, with error message
- Auto-scrolls to bottom as new events arrive

#### `StatusBadge.tsx`
- Simple colored dot + label:
  - `idle` → gray dot
  - `running` → pulsing blue dot
  - `done` → green dot
  - `error` → red dot

#### `types.ts`
- Minimal AG-UI event type definitions (not the full SDK — just what we render):
```typescript
type EventType = 
  | "RUN_STARTED" | "RUN_FINISHED" | "RUN_ERROR"
  | "STEP_STARTED" | "STEP_FINISHED"
  | "TEXT_MESSAGE_START" | "TEXT_MESSAGE_CONTENT" | "TEXT_MESSAGE_END";

interface BaseEvent { type: EventType; timestamp?: number; }
interface RunStartedEvent extends BaseEvent { type: "RUN_STARTED"; threadId: string; runId: string; }
// ... etc for each event type we care about
```

#### `api.ts`
```typescript
const BASE_URL = "http://localhost:8001";

export async function fetchAgents() {
  const res = await fetch(`${BASE_URL}/agents`);
  return res.json();
}
// POST /agui is handled by the hook directly (needs streaming)
```

### Styling

- Use plain CSS or Tailwind (whichever is simpler to set up with Vite)
- Dark theme preferred (matches terminal aesthetics)
- Monospace font for the event stream output
- Minimal — no component library needed

---

## Dependencies

```json
{
  "dependencies": {
    "react": "^18.3",
    "react-dom": "^18.3"
  },
  "devDependencies": {
    "@types/react": "^18.3",
    "@types/react-dom": "^18.3",
    "@vitejs/plugin-react": "^4",
    "typescript": "^5",
    "vite": "^5"
  }
}
```

No AG-UI client SDK needed — we parse SSE manually (keeps it simple and educational).

---

## How to run

```bash
# Terminal 1 — backend (Phase 1)
cd "C:\Users\Mindrix\Documents\Projects\Opus 4.6"
uvicorn agui_server:app --reload --port 8001

# Terminal 2 — frontend
cd "C:\Users\Mindrix\Documents\Projects\Opus 4.6\agui-frontend"
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## Verification commands

```bash
# 1. Frontend builds without errors
cd agui-frontend && npm run build

# 2. Dev server starts
npm run dev
# → should print "Local: http://localhost:5173"

# 3. Manual browser checks (with backend running on :8001):
# - Open http://localhost:5173
# - Agent dropdown shows: schema, api, core, test
# - Task dropdown shows all tasks from registry
# - Type instruction, click Run Agent
# - Status changes to "running" (blue pulse)
# - Events stream in one by one in the output panel
# - On completion, status changes to "done" (green)
# - Output panel auto-scrolled to bottom
```

---

## Acceptance criteria

- [ ] `npm run build` completes without errors
- [ ] `npm run dev` starts dev server on port 5173
- [ ] App loads in browser without console errors
- [ ] Agent dropdown populated from `GET /agents`
- [ ] Task dropdown populated from `GET /agents`
- [ ] Clicking "Run Agent" sends `POST /agui` with correct body
- [ ] Events appear in real time as SSE data arrives (not all at once)
- [ ] `TEXT_MESSAGE_CONTENT` deltas rendered as monospace text
- [ ] `RUN_STARTED` and `RUN_FINISHED` shown with visual markers
- [ ] `RUN_ERROR` shown in red with error message
- [ ] Status badge transitions: idle → running → done/error
- [ ] Output panel auto-scrolls during streaming
- [ ] "Run Agent" button disabled while a run is in progress
- [ ] No CORS errors in browser console
- [ ] `agui-frontend/README.md` documents setup and usage
- [ ] `docs/agui.md` updated with Phase 2 section

---

## Out of scope

- No parallel agent visualization (future)
- No conversation history / persistence
- No CopilotKit or AG-UI client SDK (we parse SSE manually)
- No agent output syntax highlighting
- No authentication

---

## Context for the implementing agent

**Working directory:** Project root

**Prerequisite check:** Before starting, verify Phase 1 works:
```bash
curl -s http://localhost:8001/health
# Must return: {"status": "ok", "service": "agui-agent-runner"}
```

**Read first:**
1. `agui_server.py` — understand the endpoints and input model
2. `agent_runner/agui_adapter.py` — understand the event types emitted
3. `specs/agui_phase1.md` — understand the event flow

**Create:**
1. `agui-frontend/` — entire directory structure as specified
2. Update `docs/agui.md` — append Phase 2 section

**Do not modify** any Python files from Phase 1.
