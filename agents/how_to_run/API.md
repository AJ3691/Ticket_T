## How to Run This Agent

### Using Claude Code
```bash
# From the repo root (Phase 1 must be complete):
claude "Read agents/agent_api.md and prompts/create_api.md. Execute the task. Create all files specified. Run all verification commands. Report results."
```

### Manual verification after agent finishes
```bash
# Compile check
python -m py_compile app/main.py && echo "[PASS] main compiles"

# Import check
python -c "from app.main import app; print('[PASS] app imports')"

# Route registration check
python -c "
from app.main import app
routes = [r.path for r in app.routes]
assert '/recommendations' in routes, 'Missing /recommendations'
assert '/health' in routes, 'Missing /health'
assert '/metrics' in routes, 'Missing /metrics'
print(f'[PASS] routes registered: {routes}')
"

# Validation error format check (requires Core to be done for full test)
python -c "
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

# Empty body -> 422
r = client.post('/recommendations', json={})
assert r.status_code == 422, f'Expected 422, got {r.status_code}'
body = r.json()
assert 'detail' in body, 'Missing detail in 422 response'
print('[PASS] empty body -> 422 with detail')

# Missing description -> 422
r = client.post('/recommendations', json={'title': 'test'})
assert r.status_code == 422, f'Expected 422, got {r.status_code}'
print('[PASS] missing description -> 422')

# Empty title -> 422
r = client.post('/recommendations', json={'title': '', 'description': 'test'})
assert r.status_code == 422, f'Expected 422, got {r.status_code}'
print('[PASS] empty title -> 422')

# Invalid JSON -> 422
r = client.post('/recommendations', content=b'not json', headers={'Content-Type': 'application/json'})
assert r.status_code == 422, f'Expected 422, got {r.status_code}'
print('[PASS] invalid JSON -> 422')

# Health check
r = client.get('/health')
assert r.status_code == 200
assert r.json() == {'status': 'ok'}
print('[PASS] /health -> 200')

# Metrics check
r = client.get('/metrics')
assert r.status_code == 200
m = r.json()
assert 'request_count' in m, 'Missing request_count'
assert 'error_count' in m, 'Missing error_count'
assert 'total_latency_ms' in m, 'Missing total_latency_ms'
print(f'[PASS] /metrics -> {m}')
"
```

### Verify telemetry tracks errors
```bash
python -c "
from fastapi.testclient import TestClient
from app.main import app, _metrics

client = TestClient(app)
before_errors = _metrics['error_count']
before_count = _metrics['request_count']

# Make a bad request
client.post('/recommendations', json={})

after_errors = _metrics['error_count']
after_count = _metrics['request_count']

assert after_count > before_count, 'request_count did not increment'
assert after_errors > before_errors, 'error_count did not increment for 422'
print(f'[PASS] telemetry tracks errors (errors: {before_errors} -> {after_errors})')
print(f'[PASS] telemetry tracks requests (count: {before_count} -> {after_count})')
"
```