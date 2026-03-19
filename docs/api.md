# API Reference

Base URL: `http://localhost:8000`

---

## Endpoints

### POST /recommendations

Submit a support ticket. Returns ranked recommendations.

**Request**

```
POST /recommendations
Content-Type: application/json
```

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `title` | string | yes | min length 1 | — |
| `description` | string | yes | min length 1 | — |
| `top_n` | integer | no | 1–10 | 3 |

**Example request**

```bash
curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cannot log in",
    "description": "I reset my password but still get an error",
    "top_n": 3
  }' | python -m json.tool
```

**Example response — 200 OK**

```json
{
    "recommendations": [
        {
            "action": "Verify account status and recent lockouts",
            "confidence": 0.14,
            "why": "Login failures after reset often correlate with lockouts or disabled accounts."
        },
        {
            "action": "Check auth provider error logs for this user",
            "confidence": 0.12,
            "why": "The error may be coming from the identity provider, not the app."
        },
        {
            "action": "Ask user for exact error code and timestamp",
            "confidence": 0.1,
            "why": "Pinpointing the time and error code speeds up correlation across systems."
        }
    ]
}
```

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| `recommendations` | array | Ordered list, highest confidence first |
| `recommendations[].action` | string | Recommended next step |
| `recommendations[].confidence` | float | Relevance score [0.0–1.0] |
| `recommendations[].why` | string | 1–2 sentence rationale |

**Fallback — no category matched**

If no keywords match any category, returns 3 default recommendations with low confidence (0.30, 0.25, 0.20).

---

### GET /health

Service liveness check.

```bash
curl http://localhost:8000/health
```

**Response — 200 OK**

```json
{"status": "ok"}
```

---

### GET /metrics

Request telemetry. Resets on server restart.

```bash
curl http://localhost:8000/metrics | python -m json.tool
```

**Response — 200 OK**

```json
{
    "request_count": 12,
    "error_count": 2,
    "total_latency_ms": 43.7
}
```

| Field | Type | Description |
|-------|------|-------------|
| `request_count` | integer | Total requests received (all routes) |
| `error_count` | integer | Requests that returned status ≥ 400 |
| `total_latency_ms` | float | Cumulative response time across all requests |

---

## Error Responses

All validation errors return `422 Unprocessable Entity` with field-level detail.

**Example — empty title**

```bash
curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"title": "", "description": "test"}'
```

```json
{
    "detail": [
        {
            "type": "string_too_short",
            "loc": ["body", "title"],
            "msg": "String should have at least 1 character",
            "input": "",
            "ctx": {"min_length": 1}
        }
    ]
}
```

**Validation error cases**

| Input | Status | Error type |
|-------|--------|------------|
| Empty body `{}` | 422 | missing required fields |
| Missing `title` | 422 | missing field |
| Missing `description` | 422 | missing field |
| `title: ""` | 422 | string_too_short |
| `description: ""` | 422 | string_too_short |
| `top_n: 0` | 422 | greater_than_equal (ge=1) |
| `top_n: 11` | 422 | less_than_equal (le=10) |
| Malformed JSON | 422 | JSON parse error |
| Wrong content type | 422 | content type error |

---

## Determinism

Same input always returns identical output. Verified by calling the endpoint twice:

```bash
R1=$(curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"title":"Cannot log in","description":"password reset error"}')

R2=$(curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"title":"Cannot log in","description":"password reset error"}')

[ "$R1" = "$R2" ] && echo "PASS deterministic" || echo "FAIL"
```

---

## Supported Categories

Tickets are scored against 6 categories. Confidence reflects keyword match density × category weight.

| Category | Keywords (sample) | Weight |
|----------|--------------------|--------|
| `auth` | login, password, reset, locked, token, session, mfa | 0.95 |
| `access` | permission, denied, forbidden, role, admin, unauthorized | 0.90 |
| `billing` | invoice, charge, refund, subscription, payment, plan | 0.85 |
| `performance` | slow, timeout, latency, crash, freeze, memory | 0.80 |
| `data` | sync, missing, corrupt, backup, export, migration | 0.75 |
| `integration` | api, webhook, oauth, sdk, third-party, graphql | 0.70 |
