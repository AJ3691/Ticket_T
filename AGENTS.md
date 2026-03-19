# AGENTS.md

> Master concurrency contract for the Support Ticket Triage service.
> This file is the single source of truth for agent coordination.

---

## Concurrency Contract

**Total agents:** 4 (Schema, API, Core, Test)
**Concurrent pair:** API + Core (Phase 2 — independent files, shared frozen contract)

### Agent Map

| Agent      | Owned Files                                                    | Phase | Concurrency  |
| ---------- | -------------------------------------------------------------- | ----- | ------------ |
| **Schema** | `app/models.py`, `app/rules/base.py`, `requirements.txt`       | 1     | solo         |
| **API**    | `app/main.py`                                                  | 2     | **parallel** |
| **Core**   | `app/engine.py`, `app/rules/keyword.py`, `app/rules/config.py` | 2     | **parallel** |
| **Test**   | `tests/test_engine.py`, `tests/test_api.py`                    | 3     | solo         |

### Prompt Map

Each agent has one **build prompt** (Phase build) and zero or more **reusable prompts** (ad-hoc tasks).

**Pattern:** `claude "Read agents/{agent}.md and prompts/{task}.md. Execute the task."`

| Agent | Build Prompt | Reusable Prompts |
|-------|-------------|-----------------|
| **Schema** | [`create_schema.md`](prompts/create_schema.md) | — |
| **API** | [`create_api.md`](prompts/create_api.md) | [`add_endpoint.md`](prompts/add_endpoint.md), [`add_telemetry.md`](prompts/add_telemetry.md), [`improve_error_handling.md`](prompts/improve_error_handling.md) |
| **Core** | [`create_core.md`](prompts/create_core.md) | [`add_strategy.md`](prompts/add_strategy.md) |
| **Test** | [`create_tests.md`](prompts/create_tests.md) | [`add_tests.md`](prompts/add_tests.md) |

### Expected Outputs per Agent

**Schema Agent (Phase 1):**
- `app/models.py` — frozen Pydantic models: `TicketInput`, `Recommendation`, `TriageResponse`
- `app/rules/base.py` — frozen abstract interface: `TriageStrategy.recommend()`
- `requirements.txt` — pinned project dependencies
- Validation: empty strings rejected, confidence bounded [0,1], top_n bounded [1,10]
- Deliverable gate: 8 verification checks

**API Agent (Phase 2 — parallel):**
- `app/main.py` — FastAPI app with 3 routes + telemetry middleware
- `POST /recommendations` — accepts `TicketInput`, returns `TriageResponse`, delegates to engine
- `GET /health` — returns `{"status": "ok"}`
- `GET /metrics` — returns `{request_count, error_count, total_latency_ms}`
- Telemetry middleware tracking latency and error count on every request
- Validation: 8 error cases return structured 422 responses
- Deliverable gate: 12 verification checks

**Core Agent (Phase 2 — parallel):**
- `app/engine.py` — entry point: `get_recommendations(title, description, top_n) → list[Recommendation]`
- `app/rules/keyword.py` — `KeywordStrategy` with 6+ categories, 10+ keywords each, deterministic scoring
- `app/rules/config.py` — strategy selector: `get_rule() → TriageStrategy`
- Deterministic ranking: same input → identical output every call
- Confidence sorted descending, ties broken by category key alphabetical
- Fallback behavior for unmatched input (3 default recommendations)
- Deliverable gate: 10 verification checks

**Test Agent (Phase 3):**
- `tests/test_engine.py` — 11 unit tests: determinism, sorting, top_n, fallback, multi-category, valid objects, interface
- `tests/test_api.py` — 15 integration tests: happy path, validation errors, health, metrics, telemetry, determinism via HTTP
- Deliverable gate: `pytest -v` passes with 0 failures (26+ tests)

### Scope Split

```
Phase 1 (serial)     Phase 2 (parallel)           Phase 3 (serial)
┌──────────────┐     ┌──────────────┐              ┌──────────────┐
│ Schema Agent │     │  API Agent   │              │  Test Agent  │
│              │     │  app/main.py │              │  tests/      │
│ models.py    │────▶│              │────────┐     │              │
│ base.py      │     └──────────────┘        ├────▶│              │
│ requirements │     ┌──────────────┐        │     │              │
│              │────▶│  Core Agent  │────────┘     │              │
│              │     │  engine.py   │              │              │
│  FREEZE      │     │  keyword.py  │              │              │
│              │     │  config.py   │              │              │
└──────────────┘     └──────────────┘              └──────────────┘
```

### Conflict-Avoidance Mechanism

**File ownership.** Each agent writes only to its owned files. No exceptions.

| Rule                     | Enforcement                                                 |
| ------------------------ | ----------------------------------------------------------- |
| No cross-boundary writes | Agent instructions list owned + no-touch files              |
| Frozen contracts         | `models.py` and `base.py` are read-only after Phase 1       |
| Failure protocol         | If blocked, STOP and report — never guess across boundaries |
| No shared mutable state  | Agents share contracts, not runtime state                   |

### Integration Contract (frozen in Phase 1)

```python
# Request shape (app/models.py)
TicketInput(title: str, description: str, top_n: int = 3)

# Response shape (app/models.py)
TriageResponse(recommendations: list[Recommendation])
Recommendation(action: str, confidence: float, why: str)

# Strategy interface (app/rules/base.py)
TriageStrategy.recommend(title, description, top_n) → list[Recommendation]

# Engine entry point (app/engine.py — produced by Core)
get_recommendations(title, description, top_n) → list[Recommendation]
```

---

## How to Run + Test

### Phase 1: Schema Agent (solo)
```bash
claude "Read agents/agent_schema.md and prompts/create_schema.md. Execute the task. Create all files specified. Run all verification commands. Report results."

# Verify
python -m py_compile app/models.py && echo "✓ models"
python -m py_compile app/rules/base.py && echo "✓ base"
```

### Phase 2: API + Core Agents (parallel — two terminal windows)
```bash
# Terminal 1 — API Agent
claude "Read agents/agent_api.md and prompts/create_api.md. Execute the task. Create all files specified. Run all verification commands. Report results."

# Terminal 2 — Core Agent (run simultaneously)
claude "Read agents/agent_core.md and prompts/create_core.md. Execute the task. Create all files specified. Run all verification commands. Report results."
```

### Phase 2 Integration Check (after both finish)
```bash
python -m py_compile app/main.py && echo "✓ main compiles"
python -m py_compile app/engine.py && echo "✓ engine compiles"
python -c "from app.main import app; print('✓ app imports')"
python -c "
from app.engine import get_recommendations
result = get_recommendations('Cannot log in', 'Password reset not working')
assert len(result) > 0, 'No recommendations returned'
assert result[0].confidence >= result[-1].confidence, 'Not sorted by confidence'
print(f'✓ engine returns {len(result)} recommendations, sorted correctly')
"
```

### Phase 3: Test Agent (solo)
```bash
claude "Read agents/agent_tests.md and prompts/create_tests.md. Execute the task. Create all files specified. Run all verification commands. Report results."

# Final verification
pytest -v
```

### Full-stack smoke test (after all phases)
```bash
uvicorn app.main:app --port 8000 &
sleep 2

# Happy path
curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"title": "Cannot log in", "description": "I reset my password but still get an error"}' | python -m json.tool

# Determinism
RESP1=$(curl -s -X POST http://localhost:8000/recommendations -H "Content-Type: application/json" -d '{"title":"test","description":"test"}')
RESP2=$(curl -s -X POST http://localhost:8000/recommendations -H "Content-Type: application/json" -d '{"title":"test","description":"test"}')
[ "$RESP1" = "$RESP2" ] && echo "✓ deterministic" || echo "✗ non-deterministic"

# Error handling
curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"title": ""}' | python -m json.tool

kill %1
```

---

## Definition of Done

Agent-generated work is complete only when ALL of the following are true:

- [ ] `pytest -v` passes with 0 failures
- [ ] Same input → same output (determinism verified)
- [ ] Invalid payloads return 422 with field-level errors
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `GET /metrics` returns request_count, error_count, total_latency_ms
- [ ] No TODO/FIXME in any source file
- [ ] No secrets or API keys in code
- [ ] No external network dependencies at runtime

---

## Task Templates

### Build Prompts (run once per phase)

**Phase 1 — Schema:**
```bash
claude "Read agents/agent_schema.md and prompts/create_schema.md. Execute the task. Create all files specified. Run all verification commands. Report results."
```

**Phase 2 — API (Terminal 1):**
```bash
claude "Read agents/agent_api.md and prompts/create_api.md. Execute the task. Create all files specified. Run all verification commands. Report results."
```

**Phase 2 — Core (Terminal 2):**
```bash
claude "Read agents/agent_core.md and prompts/create_core.md. Execute the task. Create all files specified. Run all verification commands. Report results."
```

**Phase 3 — Tests:**
```bash
claude "Read agents/agent_tests.md and prompts/create_tests.md. Execute the task. Create all files specified. Run all verification commands. Report results."
```

### Reusable Prompts (run anytime, as many times as needed)

**Add endpoint:**
```bash
claude "Read agents/agent_api.md and prompts/add_endpoint.md. Add a [METHOD] [/path] route. Accept [input], return [output]. Run verification."
```

**Add telemetry:**
```bash
claude "Read agents/agent_api.md and prompts/add_telemetry.md. Add [metric] tracking to the middleware. Run verification."
```

**Improve error handling:**
```bash
claude "Read agents/agent_api.md and prompts/improve_error_handling.md. Review app/main.py for unhandled edge cases. Fix gaps. Run verification."
```

**Add strategy:**
```bash
claude "Read agents/agent_core.md and prompts/add_strategy.md. [Add category / Create strategy / Improve scoring]. Preserve determinism. Run verification."
```

**Add tests:**
```bash
claude "Read agents/agent_tests.md and prompts/add_tests.md. Add tests for [behavior]. Run pytest -v."
```

---

## Repo Layout

```
├── AGENTS.md                         ← you are here (master contract)
├── agents/
│   ├── _TEMPLATE_AGENT.md            ← reusable agent template
│   ├── agent_schema.md               ← Phase 1: contracts
│   ├── agent_api.md                  ← Phase 2: HTTP layer
│   ├── agent_core.md                 ← Phase 2: recommendation engine
│   └── agent_tests.md               ← Phase 3: test suite
├── prompts/
│   ├── _TEMPLATE_PROMPT.md           ← reusable prompt template
│   ├── create_schema.md              ← build: models + base
│   ├── create_api.md                 ← build: routes + middleware
│   ├── create_core.md                ← build: engine + strategy
│   ├── create_tests.md               ← build: full test suite
│   ├── add_endpoint.md               ← reusable: API agent
│   ├── add_telemetry.md              ← reusable: API agent
│   ├── improve_error_handling.md     ← reusable: API agent
│   ├── add_strategy.md              ← reusable: Core agent
│   └── add_tests.md                  ← reusable: Test agent
├── app/
│   ├── __init__.py
│   ├── main.py                       ← API Agent owns
│   ├── models.py                     ← Schema Agent owns (frozen)
│   ├── engine.py                     ← Core Agent owns
│   └── rules/
│       ├── __init__.py
│       ├── base.py                   ← Schema Agent owns (frozen)
│       ├── keyword.py                ← Core Agent owns
│       └── config.py                 ← Core Agent owns
├── tests/
│   ├── test_engine.py                ← Test Agent owns
│   └── test_api.py                   ← Test Agent owns
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   ├── api.md
│   └── feature_slice_analysis.md
├── requirements.txt
├── Dockerfile
└── README.md
```
