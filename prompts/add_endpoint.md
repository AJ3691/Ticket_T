# Task: Add Endpoint

> **Target Agent:** agent_api
> **Phase:** any  |  **Priority:** P1  |  **Estimated Scope:** small

---

## Goal

Add or update an API endpoint in `app/main.py` while preserving the current architecture, contracts, and telemetry.

---

## How to Use

Pair this prompt with a specific instruction:
```bash
# Example: add a GET endpoint for categories
claude "Read agents/agent_api.md and prompts/add_endpoint.md. Add GET /categories that returns the list of supported ticket categories. Run verification."

# Example: add top_n query parameter to health
claude "Read agents/agent_api.md and prompts/add_endpoint.md. Add a GET /recommendations/{category} endpoint. Run verification."
```

---

## Inputs

| Input | Location | Status |
|-------|----------|--------|
| `app/main.py` | `app/main.py` | exists — modify |
| `app/models.py` | `app/models.py` | frozen — read only |
| `app/engine.py` | `app/engine.py` | read only |

---

## Process

1. Read `app/main.py` to understand existing routes and middleware
2. Read `app/models.py` to confirm available contracts
3. Determine if the change is transport-layer only or needs engine coordination
4. Implement the smallest safe change in `app/main.py`
5. Ensure the new route is tracked by telemetry middleware (automatic if using `@app`)
6. Run verification

---

## Constraints

- Keep route logic thin — delegate business logic to engine
- Do not import from `app/rules/` directly
- Do not modify `app/models.py` unless explicitly required (and document why)
- Do not modify `app/engine.py` or `app/rules/`
- New routes must be tracked by existing telemetry middleware
- Use Pydantic for any new request/response models

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
python -c "from app.main import app; print([r.path for r in app.routes])"
pytest -v
```

---

## Deliverable Summary

Return:
- Files changed: `app/main.py` (and `app/models.py` only if explicitly required)
- Route added/changed: method, path, input, output
- Contract impact: none | describe
- Telemetry: confirmed new route is tracked by middleware
