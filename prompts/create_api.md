# Task: Create API Layer

> **Target Agent:** agent_api
> **Phase:** 2  |  **Priority:** P0  |  **Estimated Scope:** medium

---

## Goal

Create `app/main.py` — the FastAPI application with routes, validation error handling, and telemetry middleware. This runs in parallel with the Core Agent.

---

## Context

### Current State
- Phase 1 complete: `app/models.py` and `app/rules/base.py` exist and are frozen
- `requirements.txt` exists with fastapi, pydantic, uvicorn, pytest, httpx
- `app/engine.py` may or may not exist yet (Core Agent runs in parallel)

### Trigger
- Phase 2 kickoff — API and Core agents start simultaneously

---

## Inputs

| Input | Location | Status |
|-------|----------|--------|
| `app/models.py` | `app/models.py` | frozen — do not modify |
| `app/rules/base.py` | `app/rules/base.py` | frozen — do not modify |
| `docs/api.md` | `docs/api.md` | reference for endpoint contract |

---

## Expected Output

| Output | Location | Shape |
|--------|----------|-------|
| `app/main.py` | `app/main.py` | FastAPI app with routes + middleware |

---

## Spec: What to Create

### `app/main.py`

Create a FastAPI application with the following components:

#### 1. Imports and Setup
```python
import logging
import time
from fastapi import FastAPI, Request
from app.engine import get_recommendations
from app.models import TicketInput, TriageResponse
```

#### 2. Logging Configuration
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("ticket_triage")
```

#### 3. Telemetry Metrics Store
```python
_metrics: dict[str, int | float] = {
    "request_count": 0,
    "error_count": 0,
    "total_latency_ms": 0.0,
}
```

Expose `_metrics` at module level so tests can inspect it.

#### 4. FastAPI App
```python
app = FastAPI(
    title="Support Ticket Triage",
    description="Returns ranked recommendations for incoming support tickets.",
    version="0.1.0",
)
```

#### 5. Telemetry Middleware

Must track every request:
- Increment `request_count` on every request
- Measure elapsed time in milliseconds using `time.perf_counter()`
- Accumulate into `total_latency_ms`
- Increment `error_count` for any response with status >= 400
- Log: `method=POST path=/recommendations status=200 latency_ms=12.3`

```python
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    _metrics["request_count"] += 1
    _metrics["total_latency_ms"] += elapsed_ms
    if response.status_code >= 400:
        _metrics["error_count"] += 1

    logger.info(
        "method=%s path=%s status=%d latency_ms=%.1f",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response
```

#### 6. Routes

**POST /recommendations**
- Accept `TicketInput` (validated by Pydantic automatically)
- Call `get_recommendations(title=ticket.title, description=ticket.description, top_n=ticket.top_n)`
- Return `TriageResponse(recommendations=result)`
- No business logic in the handler — delegate everything to engine

**GET /health**
- Return `{"status": "ok"}`

**GET /metrics**
- Return the `_metrics` dict directly

---

## Error Handling Behavior

FastAPI + Pydantic handle validation automatically. The API Agent must NOT add manual validation checks. Expected behavior:

| Input | Expected Status | Expected Response |
|-------|----------------|-------------------|
| Valid payload | 200 | `TriageResponse` JSON |
| Empty body `{}` | 422 | `{"detail": [{field errors}]}` |
| Missing `title` | 422 | Detail includes "title" field |
| Missing `description` | 422 | Detail includes "description" field |
| Empty title `""` | 422 | Detail includes min_length violation |
| Empty description `""` | 422 | Detail includes min_length violation |
| `top_n: 0` | 422 | Detail includes ge=1 violation |
| `top_n: 11` | 422 | Detail includes le=10 violation |
| Invalid JSON body | 422 | JSON parse error detail |
| Wrong content type | 422 | Content type error |

All 422 responses must increment `error_count` in telemetry.

---

## Constraints

- Do not implement ranking logic — delegate to `get_recommendations()`
- Do not import from `app/rules/` directly — only through `app/engine`
- Do not modify `app/models.py` — frozen contract
- Do not create test files — owned by Test Agent
- Do not add external dependencies beyond fastapi, uvicorn, stdlib
- No secrets or API keys
- Keep `main.py` under 80 lines

---

## Process

1. Read `app/models.py` to confirm contract shapes
2. Read `docs/api.md` for endpoint specification
3. Create `app/main.py` with all components
4. Run compile check
5. Run import check
6. Run route registration check
7. Run validation error format checks
8. Run telemetry tracking checks

---

## No-Touch Boundaries

| File/Dir | Reason |
|----------|--------|
| `app/models.py` | Frozen after Phase 1 |
| `app/rules/base.py` | Frozen after Phase 1 |
| `app/engine.py` | Owned by Core Agent |
| `app/rules/keyword.py` | Owned by Core Agent |
| `app/rules/config.py` | Owned by Core Agent |
| `tests/` | Owned by Test Agent |

---

## Verification

```bash
# 1. Compile check
python -m py_compile app/main.py && echo "✓ compiles"

# 2. Import check
python -c "from app.main import app; print('✓ app imports')"

# 3. Route registration
python -c "
from app.main import app
routes = [r.path for r in app.routes]
assert '/recommendations' in routes, 'Missing /recommendations'
assert '/health' in routes, 'Missing /health'
assert '/metrics' in routes, 'Missing /metrics'
print(f'✓ routes: {routes}')
"

# 4. Validation — empty body
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.post('/recommendations', json={})
assert r.status_code == 422, f'Expected 422, got {r.status_code}'
assert 'detail' in r.json()
print('✓ empty body → 422')
"

# 5. Validation — missing description
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.post('/recommendations', json={'title': 'test'})
assert r.status_code == 422
print('✓ missing description → 422')
"

# 6. Validation — empty title
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.post('/recommendations', json={'title': '', 'description': 'test'})
assert r.status_code == 422
print('✓ empty title → 422')
"

# 7. Validation — top_n out of range
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.post('/recommendations', json={'title': 'x', 'description': 'y', 'top_n': 0})
assert r.status_code == 422
r2 = c.post('/recommendations', json={'title': 'x', 'description': 'y', 'top_n': 11})
assert r2.status_code == 422
print('✓ top_n=0 → 422, top_n=11 → 422')
"

# 8. Validation — invalid JSON
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.post('/recommendations', content=b'not json', headers={'Content-Type': 'application/json'})
assert r.status_code == 422
print('✓ invalid JSON → 422')
"

# 9. Health endpoint
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.get('/health')
assert r.status_code == 200
assert r.json() == {'status': 'ok'}
print('✓ /health → 200')
"

# 10. Metrics endpoint
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.get('/metrics')
assert r.status_code == 200
m = r.json()
assert 'request_count' in m
assert 'error_count' in m
assert 'total_latency_ms' in m
print(f'✓ /metrics → {m}')
"

# 11. Telemetry tracks errors
python -c "
from fastapi.testclient import TestClient
from app.main import app, _metrics
c = TestClient(app)
before = _metrics['error_count']
c.post('/recommendations', json={})
after = _metrics['error_count']
assert after > before, f'error_count did not increment: {before} → {after}'
print(f'✓ error_count incremented: {before} → {after}')
"

# 12. Telemetry tracks latency
python -c "
from fastapi.testclient import TestClient
from app.main import app, _metrics
c = TestClient(app)
before = _metrics['total_latency_ms']
c.get('/health')
after = _metrics['total_latency_ms']
assert after > before, 'total_latency_ms did not increase'
print(f'✓ latency tracked: {before:.1f} → {after:.1f}')
"
```

---

## Deliverable Summary

Return:
- Files created: `app/main.py`
- What was created: FastAPI app with 3 routes, telemetry middleware, structured logging
- Contract impact: None — consumes frozen contracts only
- Tests affected: None — Test Agent creates tests in Phase 3

---

## Rollback Signal

If this task produces incorrect output:
- Delete `app/main.py` and recreate from scratch
- Signal: compile fails, routes missing, validation not returning 422, telemetry not tracking
- Notify: Orchestrator — Phase 2 integration check will fail
