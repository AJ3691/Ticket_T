# AG-UI Frontend

Minimal React frontend for the AG-UI agent runner backend.

## Run

Start the backend from the project root:

```powershell
uvicorn agui_server:app --reload --port 8002
```

Start the frontend:

```powershell
cd agui-frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Backend URL

The app defaults to `http://localhost:8002`, matching the current Phase 1 AG-UI backend docs.
Override it with:

```powershell
$env:VITE_AGUI_BASE_URL="http://localhost:8001"
npm run dev
```

## Build

```powershell
npm run build
```

## Flow

1. Agent Runner mode loads agents and tasks from `GET /agents`.
2. Agent Runner mode posts a run request to `POST /agui`.
3. LangGraph Triage mode posts ticket text to `POST /agui/triage`.
4. The hook reads the `text/event-stream` response.
5. Events are rendered as they arrive.
