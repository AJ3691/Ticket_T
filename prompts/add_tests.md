# Task: Add or Strengthen Tests

> **Target Agent:** agent_tests
> **Phase:** any  |  **Priority:** P1  |  **Estimated Scope:** small

---

## Goal

Add or strengthen specific tests for an existing behavior without changing source code. Use this prompt after the initial test suite exists and you need to cover a new case or tighten an assertion.

---

## How to Use

Pair this prompt with a specific instruction:
```bash
# Example: add a test for tie-breaking behavior
claude "Read agents/agent_tests.md and prompts/add_tests.md. Add a test for tie-breaking when two categories have equal confidence. Run verification."

# Example: strengthen validation tests
claude "Read agents/agent_tests.md and prompts/add_tests.md. Add tests for top_n=1 and top_n=10 edge cases. Run verification."

# Example: add telemetry test
claude "Read agents/agent_tests.md and prompts/add_tests.md. Add a test proving total_latency_ms increases after requests. Run verification."
```

---

## Inputs

| Input | Location | Status |
|-------|----------|--------|
| `tests/test_engine.py` | `tests/test_engine.py` | exists — append to |
| `tests/test_api.py` | `tests/test_api.py` | exists — append to |
| All `app/` source files | `app/` | read-only reference |

---

## Process

1. Read the specific behavior you need to prove
2. Read the relevant source file to understand actual implementation
3. Decide which test file: `test_engine.py` for unit, `test_api.py` for integration
4. Write a focused test with exact assertions
5. Run `pytest -v` to confirm the new test passes alongside existing tests
6. Confirm 0 failures total

---

## Constraints

- Do not modify any source files in `app/`
- Do not weaken existing assertions
- Do not duplicate existing tests — check what's already covered
- Each new test function tests one behavior
- No randomness, no network calls
- Use `TestClient` for integration tests

---

## No-Touch Boundaries

| File/Dir | Reason |
|----------|--------|
| `app/` (all files) | Tests prove behavior, they don't change it |

---

## Verification

```bash
pytest -v
```

---

## Deliverable Summary

Return:
- Files modified: which test file(s)
- Tests added: name and behavior proven by each
- Source files modified: None (must be none)
- Full suite status: pass/fail count
