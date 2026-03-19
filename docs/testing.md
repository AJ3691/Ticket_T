# Test Coverage Reference

Quick reference for reviewers. Shows every test, what it proves, and the input used.

**Run all tests:** `pytest -v`
**Total:** 26 tests — 11 unit + 15 integration

---

## Unit Tests — `tests/test_engine.py`

Tests the engine and strategy layer directly. No HTTP, no server. Calls `get_recommendations()` and `KeywordStrategy` functions in isolation.

### Group 1 — Determinism

| Test | What it proves | Input |
|------|---------------|-------|
| `test_determinism` | Calling the engine twice with identical input returns byte-for-byte identical results — action, confidence, and why all match | `"Cannot log in"` + `"I reset my password but still get an error"` |

### Group 2 — Ranking & Sorting

| Test | What it proves | Input |
|------|---------------|-------|
| `test_confidence_sorted` | Results are always ordered highest confidence first — no exceptions | `"Cannot log in"` + `"Password reset not working"`, `top_n=10` |
| `test_confidence_range` | Every confidence value is within `[0.0, 1.0]` — nothing out of bounds | `"login password reset error locked"` + `"auth token session"`, `top_n=10` |
| `test_non_empty_fields` | Every `action` and `why` string is non-empty — no blank recommendations ever returned | `"Cannot log in"` + `"Password error"`, `top_n=10` |

### Group 3 — top_n Limiting

| Test | What it proves | Input |
|------|---------------|-------|
| `test_top_n_limiting` | Engine never returns more results than requested — tested for `top_n` values 1, 2, 3, 5 | `"login password error"` + `"auth issue"` |
| `test_top_n_default` | When `top_n` is not specified, at most 3 results are returned (default behaviour) | `"login issue"` + `"password not working"` |

### Group 4 — Fallback Behaviour

| Test | What it proves | Input |
|------|---------------|-------|
| `test_fallback_no_matches` | When no keywords match any category, engine still returns a list — never crashes or returns `None` | `"xyzzy gibberish"` + `"nothing matches here at all"` |
| `test_fallback_valid_objects` | Fallback results are proper `Recommendation` objects with valid confidence and non-empty strings | `"xyzzy gibberish"` + `"nothing matches"` |

### Group 5 — Category Matching

| Test | What it proves | Input |
|------|---------------|-------|
| `test_multi_category` | Input matching multiple categories returns results from more than one category — not just one winner | `"Slow login after password reset"` + `"Performance is terrible and I keep getting locked out"`, `top_n=10` |
| `test_single_category` | Input matching one category returns that category's actions as valid `Recommendation` objects | `"invoice problem"` + `"wrong charge on my billing statement"` |

### Group 6 — Strategy Interface

| Test | What it proves | Input |
|------|---------------|-------|
| `test_strategy_interface` | `KeywordStrategy` is a proper subclass of `TriageStrategy` — the contract is correctly implemented | `issubclass()` check, no input needed |

---

## Integration Tests — `tests/test_api.py`

Tests the full HTTP layer using FastAPI's `TestClient`. No real server needed. Covers routes, validation, and telemetry as a complete stack.

### Group 1 — Happy Path

| Test | What it proves | Input | Expected |
|------|---------------|-------|----------|
| `test_happy_path` | Valid request returns 200 with a non-empty recommendations list | `title` + `description` (valid) | `200`, `recommendations` list present |
| `test_response_shape` | Every recommendation in the response has `action`, `confidence`, `why` — and confidence is a float in `[0.0, 1.0]` | `title` + `description` (valid) | All 3 fields present and typed correctly |
| `test_determinism_http` | Same POST payload twice returns byte-for-byte identical JSON — determinism holds over HTTP | Same payload sent twice | `response_1 == response_2` |

### Group 2 — Validation Errors (422)

All tests in this group assert `status_code == 422`. FastAPI + Pydantic handles these automatically.

| Test | What it proves | Input sent |
|------|---------------|-----------|
| `test_empty_body` | Empty JSON object is rejected with structured error detail | `{}` |
| `test_missing_title` | Request without `title` field is rejected | `{"description": "some desc"}` |
| `test_missing_description` | Request without `description` field is rejected | `{"title": "some title"}` |
| `test_empty_title` | `title: ""` is rejected — min_length=1 enforced | `{"title": "", "description": "valid"}` |
| `test_empty_description` | `description: ""` is rejected — min_length=1 enforced | `{"title": "valid", "description": ""}` |
| `test_top_n_too_low` | `top_n: 0` is rejected — ge=1 enforced | `{"title": "x", "description": "y", "top_n": 0}` |
| `test_top_n_too_high` | `top_n: 11` is rejected — le=10 enforced | `{"title": "x", "description": "y", "top_n": 11}` |
| `test_invalid_json` | Malformed JSON body is rejected | Raw bytes `b"not json"` with JSON content-type |

### Group 3 — Other Routes

| Test | What it proves | Request | Expected |
|------|---------------|---------|----------|
| `test_health` | `GET /health` returns 200 and exact body `{"status": "ok"}` | `GET /health` | `200`, `{"status": "ok"}` |
| `test_metrics` | `GET /metrics` returns 200 with all three required fields present | `GET /metrics` | `200`, keys: `request_count`, `error_count`, `total_latency_ms` |

### Group 4 — Telemetry

| Test | What it proves | How |
|------|---------------|-----|
| `test_telemetry_request_count` | `request_count` increments on every request — middleware is firing | Read `_metrics` before and after a `GET /health`, assert `after > before` |
| `test_telemetry_error_count` | `error_count` increments when a 422 is returned — errors are tracked correctly | Read `_metrics` before and after a bad `POST /recommendations`, assert `after > before` |

---

## Manual Query Runner — `tests/test_queries.py`

Not a pytest test — a visual runner for manual exploration. Run with `python tests/test_queries.py`.

| Query | Category targeted | Purpose |
|-------|------------------|---------|
| `"Cannot log in"` | `auth` | Core auth keyword matching |
| `"Slow dashboard"` | `performance` | Performance keyword matching |
| `"Wrong invoice charge"` | `billing` | Billing keyword matching |
| `"API webhook failing"` | `integration` | Integration keyword matching |
| `"Missing data after sync"` | `data` | Data keyword matching |
| `"Access denied to admin panel"` | `access` | Access/permissions keyword matching |
| `"MFA not working"` (top_n=5) | `auth` | top_n > available results (returns 3, not 5) |
| `"Payment refund"` (top_n=2) | `billing` | top_n clipping |
| `"xyzzy gibberish"` | none | Fallback behaviour when zero keywords match |

---

## Coverage Summary

| Area | Tested by | Tests |
|------|-----------|-------|
| Engine determinism | unit + integration | `test_determinism`, `test_determinism_http` |
| Confidence sorting | unit | `test_confidence_sorted` |
| Confidence range [0,1] | unit | `test_confidence_range` |
| top_n limiting | unit | `test_top_n_limiting`, `test_top_n_default` |
| Fallback (no match) | unit | `test_fallback_no_matches`, `test_fallback_valid_objects` |
| Multi-category input | unit | `test_multi_category` |
| Single-category input | unit | `test_single_category` |
| Non-empty fields | unit | `test_non_empty_fields` |
| Strategy interface contract | unit | `test_strategy_interface` |
| Happy path HTTP | integration | `test_happy_path`, `test_response_shape` |
| HTTP determinism | integration | `test_determinism_http` |
| Missing required fields | integration | `test_missing_title`, `test_missing_description`, `test_empty_body` |
| Empty string fields | integration | `test_empty_title`, `test_empty_description` |
| top_n out of range | integration | `test_top_n_too_low`, `test_top_n_too_high` |
| Malformed JSON | integration | `test_invalid_json` |
| Health route | integration | `test_health` |
| Metrics route | integration | `test_metrics` |
| Telemetry request count | integration | `test_telemetry_request_count` |
| Telemetry error count | integration | `test_telemetry_error_count` |
