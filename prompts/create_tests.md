# Task: Create Full Test Suite

> **Target Agent:** agent_tests
> **Phase:** 3  |  **Priority:** P0  |  **Estimated Scope:** large

---

## Goal

Create the complete test suite — unit tests for engine/strategy behavior and integration tests for API behavior — proving every documented behavior with exact assertions.

---

## Context

### Current State
- Phase 1 + Phase 2 complete: all source files exist and compile
- `app/models.py` and `app/rules/base.py` frozen
- `app/main.py` has routes, middleware, telemetry
- `app/engine.py` delegates to `app/rules/keyword.py` via `app/rules/config.py`
- No test files exist yet

### Trigger
- Phase 3 kickoff — final step before submission

---

## Inputs

| Input | Location | Status |
|-------|----------|--------|
| `app/models.py` | `app/models.py` | frozen — read only |
| `app/rules/base.py` | `app/rules/base.py` | frozen — read only |
| `app/main.py` | `app/main.py` | exists — read only |
| `app/engine.py` | `app/engine.py` | exists — read only |
| `app/rules/keyword.py` | `app/rules/keyword.py` | exists — read only |

---

## Expected Output

| Output | Location | Shape |
|--------|----------|-------|
| `tests/__init__.py` | `tests/__init__.py` | Empty init |
| `tests/test_engine.py` | `tests/test_engine.py` | 11+ unit test functions |
| `tests/test_api.py` | `tests/test_api.py` | 15+ integration test functions |

---

## Spec: What to Create

### 1. `tests/__init__.py`
Empty file.

### 2. `tests/test_engine.py`

Unit tests for the engine and strategy layer. Import directly from `app.engine` and `app.rules.keyword`.

```python
import pytest
from app.engine import get_recommendations
from app.models import Recommendation
from app.rules.keyword import KeywordStrategy
from app.rules.base import TriageStrategy
```

**Required tests:**

#### `test_determinism`
Call `get_recommendations` twice with identical input. Assert every field matches.
```python
def test_determinism():
    r1 = get_recommendations("Cannot log in", "I reset my password but still get an error")
    r2 = get_recommendations("Cannot log in", "I reset my password but still get an error")
    assert len(r1) == len(r2)
    for a, b in zip(r1, r2):
        assert a.action == b.action
        assert a.confidence == b.confidence
        assert a.why == b.why
```

#### `test_confidence_sorted`
Assert results are sorted by confidence descending.
```python
def test_confidence_sorted():
    results = get_recommendations("Cannot log in", "Password reset not working", top_n=10)
    for i in range(len(results) - 1):
        assert results[i].confidence >= results[i + 1].confidence
```

#### `test_top_n_limiting`
Assert top_n is respected for multiple values.
```python
def test_top_n_limiting():
    for n in [1, 2, 3, 5]:
        results = get_recommendations("login password error", "auth issue", top_n=n)
        assert len(results) <= n
```

#### `test_top_n_default`
Call without specifying top_n. Assert at most 3 results.
```python
def test_top_n_default():
    results = get_recommendations("login issue", "password not working")
    assert len(results) <= 3
```

#### `test_fallback_no_matches`
Gibberish input returns a list (possibly fallback recommendations).
```python
def test_fallback_no_matches():
    results = get_recommendations("xyzzy gibberish", "nothing matches here at all")
    assert isinstance(results, list)
```

#### `test_fallback_valid_objects`
Fallback results are valid Recommendation objects with correct ranges.
```python
def test_fallback_valid_objects():
    results = get_recommendations("xyzzy gibberish", "nothing matches")
    for r in results:
        assert isinstance(r, Recommendation)
        assert 0.0 <= r.confidence <= 1.0
        assert len(r.action) > 0
        assert len(r.why) > 0
```

#### `test_multi_category`
Input matching multiple categories returns results from different categories.
```python
def test_multi_category():
    results = get_recommendations(
        "Slow login after password reset",
        "Performance is terrible and I keep getting locked out",
        top_n=10,
    )
    assert len(results) >= 2
    actions = [r.action for r in results]
    assert len(set(actions)) > 1  # not all the same action
```

#### `test_single_category`
Input matching only one category returns that category's actions.
```python
def test_single_category():
    results = get_recommendations("invoice problem", "wrong charge on my billing statement")
    assert len(results) >= 1
    assert all(isinstance(r, Recommendation) for r in results)
```

#### `test_confidence_range`
All confidence values within [0.0, 1.0].
```python
def test_confidence_range():
    results = get_recommendations("login password reset error locked", "auth token session", top_n=10)
    for r in results:
        assert 0.0 <= r.confidence <= 1.0, f"Out of range: {r.confidence}"
```

#### `test_non_empty_fields`
All action and why strings are non-empty.
```python
def test_non_empty_fields():
    results = get_recommendations("Cannot log in", "Password error", top_n=10)
    for r in results:
        assert len(r.action) > 0, "Empty action"
        assert len(r.why) > 0, "Empty why"
```

#### `test_strategy_interface`
KeywordStrategy is a subclass of TriageStrategy.
```python
def test_strategy_interface():
    assert issubclass(KeywordStrategy, TriageStrategy)
```

---

### 3. `tests/test_api.py`

Integration tests using FastAPI TestClient. No real HTTP server needed.

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app, _metrics
```

**Required tests:**

#### `test_happy_path`
Valid input → 200 with recommendations list.
```python
def test_happy_path():
    client = TestClient(app)
    r = client.post("/recommendations", json={
        "title": "Cannot log in",
        "description": "I reset my password but still get an error",
    })
    assert r.status_code == 200
    body = r.json()
    assert "recommendations" in body
    assert isinstance(body["recommendations"], list)
    assert len(body["recommendations"]) > 0
```

#### `test_response_shape`
Each recommendation has action, confidence, why.
```python
def test_response_shape():
    client = TestClient(app)
    r = client.post("/recommendations", json={
        "title": "Cannot log in",
        "description": "Password error",
    })
    for rec in r.json()["recommendations"]:
        assert "action" in rec
        assert "confidence" in rec
        assert "why" in rec
        assert isinstance(rec["confidence"], (int, float))
        assert 0.0 <= rec["confidence"] <= 1.0
```

#### `test_determinism_http`
Same POST twice → identical JSON.
```python
def test_determinism_http():
    client = TestClient(app)
    payload = {"title": "Cannot log in", "description": "Password reset not working"}
    r1 = client.post("/recommendations", json=payload)
    r2 = client.post("/recommendations", json=payload)
    assert r1.json() == r2.json()
```

#### `test_empty_body`
```python
def test_empty_body():
    client = TestClient(app)
    r = client.post("/recommendations", json={})
    assert r.status_code == 422
    assert "detail" in r.json()
```

#### `test_missing_title`
```python
def test_missing_title():
    client = TestClient(app)
    r = client.post("/recommendations", json={"description": "some desc"})
    assert r.status_code == 422
```

#### `test_missing_description`
```python
def test_missing_description():
    client = TestClient(app)
    r = client.post("/recommendations", json={"title": "some title"})
    assert r.status_code == 422
```

#### `test_empty_title`
```python
def test_empty_title():
    client = TestClient(app)
    r = client.post("/recommendations", json={"title": "", "description": "valid"})
    assert r.status_code == 422
```

#### `test_empty_description`
```python
def test_empty_description():
    client = TestClient(app)
    r = client.post("/recommendations", json={"title": "valid", "description": ""})
    assert r.status_code == 422
```

#### `test_top_n_too_low`
```python
def test_top_n_too_low():
    client = TestClient(app)
    r = client.post("/recommendations", json={"title": "x", "description": "y", "top_n": 0})
    assert r.status_code == 422
```

#### `test_top_n_too_high`
```python
def test_top_n_too_high():
    client = TestClient(app)
    r = client.post("/recommendations", json={"title": "x", "description": "y", "top_n": 11})
    assert r.status_code == 422
```

#### `test_invalid_json`
```python
def test_invalid_json():
    client = TestClient(app)
    r = client.post("/recommendations", content=b"not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
```

#### `test_health`
```python
def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

#### `test_metrics`
```python
def test_metrics():
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    m = r.json()
    assert "request_count" in m
    assert "error_count" in m
    assert "total_latency_ms" in m
```

#### `test_telemetry_request_count`
```python
def test_telemetry_request_count():
    client = TestClient(app)
    before = _metrics["request_count"]
    client.get("/health")
    after = _metrics["request_count"]
    assert after > before
```

#### `test_telemetry_error_count`
```python
def test_telemetry_error_count():
    client = TestClient(app)
    before = _metrics["error_count"]
    client.post("/recommendations", json={})
    after = _metrics["error_count"]
    assert after > before
```

---

## Constraints

- Do not modify any source files in `app/`
- Prefer exact assertions over loose checks
- Each test function tests one behavior
- No randomness in tests
- No external network calls
- Use `TestClient` for integration tests
- Do not mock core behavior — test real implementations
- Do not weaken assertions to make unstable code pass

---

## Process

1. Read all source files to understand actual behavior
2. Create `tests/__init__.py` (empty)
3. Create `tests/test_engine.py` with all 11 unit tests
4. Create `tests/test_api.py` with all 15 integration tests
5. Run `pytest -v`
6. Fix any test that fails due to incorrect test logic (not by changing source)
7. Confirm 0 failures

---

## No-Touch Boundaries

| File/Dir | Reason |
|----------|--------|
| `app/` (all files) | Tests prove behavior, they don't change it |

---

## Verification

```bash
# Run full suite
pytest -v

# Check test count
pytest --collect-only -q | tail -1
# Expected: 26+ tests collected

# Run only unit tests
pytest tests/test_engine.py -v

# Run only integration tests
pytest tests/test_api.py -v
```

---

## Deliverable Summary

Return:
- Files created: `tests/__init__.py`, `tests/test_engine.py`, `tests/test_api.py`
- What was created: 11 unit tests + 15 integration tests covering full Test Coverage Map
- Contract impact: None — read-only consumer
- Source files modified: None

---

## Rollback Signal

If tests fail:
- First: verify test logic is correct against actual source behavior
- If source behavior is wrong: STOP → report to orchestrator
- If test logic is wrong: fix the test, not the source
- Signal: `pytest -v` shows failures
