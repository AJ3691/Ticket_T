# Upgrades 

Incremental changes applied after initial build. Each entry covers what changed, why, and the bug it fixed or problem it solved.

---

## v0.2 — Structured JSON Logging + Request ID

**File changed:** `app/main.py`

### What changed

The telemetry middleware was upgraded from string-based logging to structured JSON logs, with a unique request ID generated per request.

**Before:**
```
2026-03-18T16:33:27 | INFO | method=POST path=/recommendations status=200 latency_ms=12.3
```

**After:**
```json
{"request_id": "a3f1c2d4-...", "method": "POST", "path": "/recommendations", "status": 200, "latency_ms": 12.3}
```

### Three specific changes

**1. Request ID (`uuid.uuid4()`)**

Every request gets a unique ID generated at middleware entry. It is:
- Included in the structured log line
- Returned to the caller as `X-Request-ID` response header

This means a client that gets an error can report their request ID, and you can pull the exact log line for that request.

**2. Structured JSON log via `logger.info(json.dumps(...))`**

The log line is now a valid JSON object. Machine-readable by log aggregators (Datadog, CloudWatch, Loki, etc.) without any parsing configuration. Previously it was a formatted string — readable to humans but awkward to query.

**3. Bug fix — error_count now correctly tracks 422s**

The original middleware checked `response.status_code >= 400` after `call_next()`. The proposed refactor moved logic into `try/except` which only caught unhandled 500s — 422 validation errors are normal responses that don't raise exceptions, so they would have silently stopped incrementing `error_count`.

Fixed by moving the status check into `finally`, which runs for every request regardless of whether an exception was raised:

```python
finally:
    ...
    if status_code >= 400:      # catches 422s AND 500s
        _metrics["error_count"] += 1
```

`test_telemetry_error_count` confirms this still passes.

### What this gives you

| Before | After |
|--------|-------|
| String logs, hard to query | JSON logs, queryable by any log tool |
| No request tracing | Every request has a unique ID |
| Errors untraceable after the fact | Client can report `X-Request-ID`, you can find the exact log |
| 500s not tracked in error_count | Both 422s and 500s increment error_count correctly |

### What it doesn't change

- `_metrics` dict shape is unchanged — `GET /metrics` response is identical
- All 26 tests pass without modification
- No new dependencies (uuid and json are stdlib)
- Route handlers and engine layer untouched
