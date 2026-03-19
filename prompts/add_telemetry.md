# Task: Add Telemetry

> **Target Agent:** agent_api
> **Phase:** any  |  **Priority:** P1  |  **Estimated Scope:** small

---

## Goal

Add or improve telemetry tracking in the middleware or metrics endpoint without breaking existing behavior.

---

## How to Use

Pair this prompt with a specific instruction:
```bash
# Example: track per-endpoint latency
claude "Read agents/agent_api.md and prompts/add_telemetry.md. Add per-endpoint latency tracking to _metrics (e.g., latency_by_path). Run verification."

# Example: add P99 latency
claude "Read agents/agent_api.md and prompts/add_telemetry.md. Track min/max/avg latency in _metrics. Run verification."

# Example: count recommendations served
claude "Read agents/agent_api.md and prompts/add_telemetry.md. Add a recommendations_served counter that increments by the number of recommendations returned. Run verification."
```

---

## Inputs

| Input | Location | Status |
|-------|----------|--------|
| `app/main.py` | `app/main.py` | exists — modify (middleware + _metrics) |

---

## Process

1. Read `app/main.py` — understand current `_metrics` dict and middleware
2. Plan the new metric (name, type, where to increment)
3. Add the metric key to `_metrics` with a sensible default
4. Add tracking logic in the middleware or route handler
5. Verify `GET /metrics` returns the new metric
6. Verify existing metrics still work

---

## Constraints

- Do not remove or rename existing metrics (`request_count`, `error_count`, `total_latency_ms`)
- Keep `_metrics` as a simple dict (no external libraries)
- Middleware must remain async-compatible
- Do not modify engine or strategy files
- Structured logging format must be preserved

---

## No-Touch Boundaries

| File/Dir | Reason |
|----------|--------|
| `app/models.py` | Frozen contract |
| `app/engine.py` | Owned by Core Agent |
| `app/rules/` | Owned by Core Agent |
| `tests/` | Owned by Test Agent |

---

## Verification

```bash
python -m py_compile app/main.py && echo "✓ compiles"

# Existing metrics still present
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
m = c.get('/metrics').json()
assert 'request_count' in m, 'Missing request_count'
assert 'error_count' in m, 'Missing error_count'
assert 'total_latency_ms' in m, 'Missing total_latency_ms'
print(f'✓ existing metrics intact: {list(m.keys())}')
"

pytest -v
```

---

## Deliverable Summary

Return:
- Files changed: `app/main.py`
- Metric added: name, type, when it increments
- Existing metrics: confirmed still present and working
- Tests affected: may need new tests (note for Test Agent)
