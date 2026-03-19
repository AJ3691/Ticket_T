# API Agent

> **Version:** 1.1  |  **Phase:** 2  |  **Concurrency:** parallel (runs alongside Core Agent)

---

## Mission

Own the HTTP transport layer — routes, request validation, error responses, and telemetry middleware — while keeping route logic thin and delegating all business logic to the engine.

---

## Task Prompt

**-> [`prompts/create_api.md`](../prompts/create_api.md)**

Contains the exact spec for `app/main.py`: routes, middleware, error handling, telemetry, and all verification commands. Feed it to the agent alongside this file.


---

## Ownership Boundary

### Owned Files (read-write)

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, routes, middleware, telemetry |

### Read-Only Dependencies

| File | Why needed |
|------|------------|
| `app/models.py` | Import TicketInput, TriageResponse (frozen — do not modify) |
| `app/engine.py` | Import `get_recommendations()` (produced by Core Agent) |
| `docs/api.md` | Endpoint contract reference |

### No-Touch Files

- `app/models.py` — frozen after Phase 1
- `app/rules/base.py` — frozen after Phase 1
- `app/engine.py` — owned by Core Agent
- `app/rules/keyword.py` — owned by Core Agent
- `app/rules/config.py` — owned by Core Agent
- `tests/` — owned by Test Agent

---

## Responsibilities

1. Implement `POST /recommendations` route that accepts `TicketInput` and returns `TriageResponse`
2. Implement `GET /health` returning `{"status": "ok"}`
3. Implement `GET /metrics` returning request_count, error_count, total_latency_ms
4. Implement telemetry middleware that tracks latency and error counts per request
5. Ensure all validation errors return structured 422 responses via Pydantic/FastAPI
6. Keep route logic thin — delegate to `get_recommendations()` from engine

---

## Shared Contract

### Consumed Contracts

| Contract | Source | Shape |
|----------|--------|-------|
| `TicketInput` | `app/models.py` | `title: str, description: str, top_n: int = 3` |
| `TriageResponse` | `app/models.py` | `recommendations: list[Recommendation]` |
| `get_recommendations()` | `app/engine.py` | `(title, description, top_n) -> list[Recommendation]` |

### Produced Contracts

| Contract | Consumers | Shape |
|----------|-----------|-------|
| `POST /recommendations` | Clients, Test Agent | JSON in -> JSON out, 200 or 422 |
| `GET /health` | Clients, Test Agent | `{"status": "ok"}` |
| `GET /metrics` | Clients, Test Agent | `{request_count, error_count, total_latency_ms}` |
| `_metrics` dict | Internal middleware | `dict[str, int or float]` |

---

## Constraints

- Route handler must NOT implement ranking logic — delegate to engine
- Route handler must NOT import from `app/rules/` directly — only through engine
- Telemetry middleware must track ALL requests, including errors
- Validation must be handled by Pydantic + FastAPI (no manual if/else checks)
- No external dependencies beyond fastapi, uvicorn, and stdlib
- No secrets or API keys
- Structured logging format: `%(asctime)s | %(levelname)s | %(message)s`

---

## Failure Protocol

| Blocker | Action |
|---------|--------|
| `get_recommendations()` not available yet (Core not done) | Create `main.py` anyway — import will resolve at runtime. Verify compile + validation tests independently. |
| Model fields don't match expected shape | STOP -> report to orchestrator, do not modify `models.py` |
| Need additional middleware or dependency | STOP -> document requirement, do not add without approval |

**Rule:** Never make speculative edits across ownership boundaries. Report and wait.

---

## Definition of Done

- [ ] `app/main.py` compiles without errors
- [ ] `POST /recommendations` route registered and delegates to engine
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `GET /metrics` returns all three counters
- [ ] Telemetry middleware tracks request_count, error_count, total_latency_ms
- [ ] Empty body -> 422 with structured detail
- [ ] Missing required fields -> 422 with field-level errors
- [ ] Empty title/description -> 422 (enforced by Pydantic min_length)
- [ ] Invalid JSON -> 422
- [ ] Error count increments on 422 responses
- [ ] No TODO/FIXME introduced
- [ ] No business logic in route handler

---

## Execution Notes

**Pre-conditions:** Phase 1 complete — `app/models.py` and `app/rules/base.py` exist and are frozen
**Post-conditions:** `app/main.py` compiles, routes registered, validation works, telemetry tracks
**Handoff:** After both API and Core agents finish, run the Phase 2 Integration Check from `AGENTS.md`
