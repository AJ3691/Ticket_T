# Test Agent

> **Version:** 1.0  |  **Phase:** 3  |  **Concurrency:** solo (runs after API + Core complete)

---

## Mission

Own the test suite and prove real behavior of the system — determinism, validation, ranking, telemetry, and endpoint contract — without masking defects or editing source files.

---

## Task Prompts

| Prompt | When to use | Scope |
|--------|------------|-------|
| **[`prompts/create_tests.md`](../prompts/create_tests.md)** | Phase 3 initial build | Create both test files from scratch |
| **[`prompts/add_tests.md`](../prompts/add_tests.md)** | Ad-hoc — add or strengthen specific tests | Add tests to existing files |

## Ownership Boundary

### Owned Files (read-write)

| File | Purpose |
|------|---------|
| `tests/__init__.py` | Package init |
| `tests/test_engine.py` | Unit tests — ranking, determinism, strategy, fallback |
| `tests/test_api.py` | Integration tests — endpoint, validation, telemetry |

### Read-Only Dependencies

| File | Why needed |
|------|------------|
| `app/models.py` | Import models for assertions |
| `app/engine.py` | Import `get_recommendations()` for unit tests |
| `app/main.py` | Import `app` and `_metrics` for integration tests |
| `app/rules/keyword.py` | Import `KeywordStrategy` for direct strategy tests |
| `app/rules/base.py` | Import `TriageStrategy` for interface compliance test |

### No-Touch Files

- `app/main.py` — owned by API Agent
- `app/engine.py` — owned by Core Agent
- `app/models.py` — frozen after Phase 1
- `app/rules/base.py` — frozen after Phase 1
- `app/rules/keyword.py` — owned by Core Agent
- `app/rules/config.py` — owned by Core Agent

---

## Responsibilities

1. Write unit tests for ranking, determinism, sorting, top_n, fallback, and strategy interface
2. Write integration tests for endpoint contract, validation errors, health, metrics, and telemetry
3. Prove determinism by calling the same function/endpoint twice and asserting identical results
4. Keep tests specific — each test proves one behavior with exact assertions
5. Keep tests deterministic — no randomness, no time-dependence, no flaky setup

---

## Test Coverage Map

### Unit Tests (`tests/test_engine.py`)

| Test | Behavior Proven |
|------|----------------|
| `test_determinism` | Same input → identical recommendations on repeated calls |
| `test_confidence_sorted` | Results sorted by confidence descending |
| `test_top_n_limiting` | Never returns more than `top_n` results |
| `test_top_n_default` | Default top_n=3 returns at most 3 |
| `test_fallback_no_matches` | Unknown input returns fallback recommendations |
| `test_fallback_valid_objects` | Fallback results are valid Recommendation objects |
| `test_multi_category` | Input matching multiple categories returns mixed results |
| `test_single_category` | Input matching one category returns that category's actions |
| `test_confidence_range` | All confidence values in [0.0, 1.0] |
| `test_non_empty_fields` | All action and why strings are non-empty |
| `test_strategy_interface` | `KeywordStrategy` is subclass of `TriageStrategy` |

### Integration Tests (`tests/test_api.py`)

| Test | Behavior Proven |
|------|----------------|
| `test_happy_path` | Valid input → 200 with recommendations list |
| `test_response_shape` | Response matches TriageResponse schema |
| `test_determinism_http` | Same POST twice → identical JSON response |
| `test_empty_body` | `{}` → 422 with detail |
| `test_missing_title` | Missing title field → 422 |
| `test_missing_description` | Missing description field → 422 |
| `test_empty_title` | `title: ""` → 422 |
| `test_empty_description` | `description: ""` → 422 |
| `test_top_n_too_low` | `top_n: 0` → 422 |
| `test_top_n_too_high` | `top_n: 11` → 422 |
| `test_invalid_json` | Malformed body → 422 |
| `test_health` | `GET /health` → `{"status": "ok"}` |
| `test_metrics` | `GET /metrics` → has request_count, error_count, total_latency_ms |
| `test_telemetry_request_count` | request_count increments on each request |
| `test_telemetry_error_count` | error_count increments on 422 |

---

## Shared Contract

### Consumed Contracts

| Contract | Source | Shape |
|----------|--------|-------|
| `get_recommendations()` | `app/engine.py` | `(title, description, top_n) → list[Recommendation]` |
| `Recommendation` | `app/models.py` | `action: str, confidence: float, why: str` |
| `TriageResponse` | `app/models.py` | `recommendations: list[Recommendation]` |
| `app` | `app/main.py` | FastAPI application instance |
| `_metrics` | `app/main.py` | `dict[str, int\|float]` |
| `KeywordStrategy` | `app/rules/keyword.py` | Concrete `TriageStrategy` |
| `TriageStrategy` | `app/rules/base.py` | Abstract base class |

### Produced Contracts

| Contract | Consumers | Shape |
|----------|-----------|-------|
| Test suite | Human reviewer, CI/CD | `pytest -v` pass/fail |

---

## Constraints

- Do not modify any source files — tests prove existing behavior, not shape it
- Prefer exact assertions over loose existence checks
- Each test function tests one behavior
- No randomness in tests
- No external network calls in tests
- Use `TestClient` from FastAPI for integration tests (no real HTTP server)
- Do not mock away core behavior — test real implementations where practical
- Do not weaken assertions to make unstable code pass

---

## Failure Protocol

| Blocker | Action |
|---------|--------|
| Source behavior contradicts documented contract | STOP → report mismatch with exact details |
| Test requires a function/field that doesn't exist | STOP → report missing dependency |
| Behavior is genuinely ambiguous | STOP → report ambiguity with the exact test you intended |

**Rule:** Never "fix" source code to make tests pass. Never weaken assertions to hide bugs. Report and wait.

---

## Definition of Done

- [ ] `tests/test_engine.py` exists with 11+ unit tests
- [ ] `tests/test_api.py` exists with 15+ integration tests
- [ ] `pytest -v` passes with 0 failures
- [ ] All tests are deterministic (no flakes)
- [ ] No source files modified
- [ ] No TODO/FIXME in test files
- [ ] Test Coverage Map above is fully covered

---

## Execution Notes

**Pre-conditions:** Phase 1 + Phase 2 complete — all source files exist and compile
**Post-conditions:** Full test suite passes, all documented behaviors proven
**Handoff:** After Test Agent completes and `pytest -v` passes, the system is ready for final smoke test and submission
