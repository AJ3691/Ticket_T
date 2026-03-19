# Task: Improve Error Handling

> **Target Agent:** agent_api
> **Phase:** any  |  **Priority:** P1  |  **Estimated Scope:** small–medium

---

## Goal

Review and strengthen error handling in the API layer — catch unhandled edge cases, improve error response clarity, and ensure all errors are tracked by telemetry.

---

## How to Use

Pair this prompt with a specific instruction or run as a general review:
```bash
# General review
claude "Read agents/agent_api.md and prompts/improve_error_handling.md. Review app/main.py for unhandled edge cases. Fix any gaps. Run verification."

# Specific: handle engine exceptions
claude "Read agents/agent_api.md and prompts/improve_error_handling.md. Add a try/except around the engine call in POST /recommendations so that if the engine raises an unexpected error, the route returns a 500 with a safe message. Run verification."

# Specific: add request size limit
claude "Read agents/agent_api.md and prompts/improve_error_handling.md. Add validation that rejects request bodies larger than 10KB. Run verification."
```

---

## Inputs

| Input | Location | Status |
|-------|----------|--------|
| `app/main.py` | `app/main.py` | exists — modify |
| `app/models.py` | `app/models.py` | frozen — read only (validation reference) |

---

## Common Error Handling Patterns

| Pattern | Where | How |
|---------|-------|-----|
| Pydantic validation errors | Automatic via FastAPI | Already handled — verify 422 responses |
| Engine raises exception | Route handler | Wrap in try/except → return 500 with safe message |
| Unexpected content type | Middleware or route | FastAPI handles — verify behavior |
| Extremely large payloads | Middleware | Add body size check if needed |
| Malformed JSON | Automatic via FastAPI | Already handled — verify 422 |

---

## Process

1. Read `app/main.py` thoroughly
2. List every request path and identify where errors can occur
3. Check: does every error path increment `error_count` in telemetry?
4. Check: does every error path return structured JSON (not raw text)?
5. Implement fixes for any gaps found
6. Run verification

---

## Constraints

- Do not change the happy-path behavior of existing routes
- All error responses must be JSON (no raw text or HTML)
- All errors must be tracked by telemetry middleware
- Do not expose internal details (stack traces, file paths) in error responses
- Do not modify engine or strategy files
- Keep route logic thin — error handling should be concise

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

# Existing validation still works
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
assert c.post('/recommendations', json={}).status_code == 422
assert c.post('/recommendations', json={'title': '', 'description': 'x'}).status_code == 422
assert c.get('/health').status_code == 200
print('✓ existing error handling intact')
"

pytest -v
```

---

## Deliverable Summary

Return:
- Files changed: `app/main.py`
- Gaps found: list each unhandled edge case
- Fixes applied: what was changed and why
- Contract impact: none (error handling only)
- Tests affected: may need new tests (note for Test Agent)
