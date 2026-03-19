# Support Ticket Triage API

![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![Tests](https://img.shields.io/badge/tests-26%20passed-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

A FastAPI service that returns ranked, deterministic recommendations for incoming support tickets using keyword-based scoring. Built entirely by concurrent AI agents from a structured harness.

> **Want to see the agents in action?** See [DEMO.md](DEMO.md) to run two agents concurrently and watch them deliver independently.

---

## Project Structure

```
├── AGENTS.md                        # Master concurrency contract — agent phases, ownership, run commands
├── run_agents.sh                    # Runs API + Core agents concurrently (bash)
├── requirements.txt                 # Python dependencies
│
├── app/
│   ├── main.py                      # FastAPI routes, telemetry middleware, structured logging
│   ├── engine.py                    # Recommendation entry point — delegates to active strategy
│   ├── models.py                    # Pydantic models: TicketInput, Recommendation, TriageResponse
│   └── rules/
│       ├── base.py                  # Abstract strategy interface (TriageStrategy)
│       ├── keyword.py               # Keyword-matching strategy — 6 categories, confidence decay
│       └── config.py                # Strategy selector — returns active TriageStrategy
│
├── agents/
│   ├── agent_api.md                 # API Agent — owns app/main.py
│   ├── agent_core.md                # Core Agent — owns engine + rules
│   ├── agent_schema.md              # Schema Agent — owns models + base (frozen after Phase 1)
│   ├── agent_tests.md               # Test Agent — owns tests/
│   ├── _TEMPLATE_AGENT.md           # Template for new agents
│   └── HOW_To RUN Agent/            # Per-agent run instructions
│       ├── API.md
│       ├── CORE.md
│       ├── Schema.md
│       └── Test.md
│
├── prompts/
│   ├── create_api.md                # Build: API layer
│   ├── create_core.md               # Build: engine + strategy
│   ├── create_schema.md             # Build: models + base
│   ├── create_tests.md              # Build: full test suite
│   ├── add_endpoint.md              # Reusable: add a route (API Agent)
│   ├── add_strategy.md              # Reusable: add/modify strategy (Core Agent)
│   ├── add_telemetry.md             # Reusable: add metrics (API Agent)
│   ├── add_tests.md                 # Reusable: add tests (Test Agent)
│   ├── improve_error_handling.md    # Reusable: harden error handling (API Agent)
│   └── _TEMPLATE_PROMPT.md          # Template for new prompts
│
├── tests/
│   ├── test_engine.py               # 11 unit tests — determinism, sorting, top_n, fallback
│   ├── test_api.py                  # 15 integration tests — endpoints, validation, telemetry
│   └── test_queries.py              # Manual query runner — visual output, not pytest
│
└── docs/
    ├── architecture.md              # Module map, request flow, interfaces, scoring algorithm
    ├── api.md                       # Endpoint contracts, curl examples, error codes
    ├── decisions.md                 # 10 key tradeoffs — chosen vs rejected, why it fits / when it breaks
    ├── testing.md                   # Full test coverage reference — grouped by behaviour
    ├── upgrades.md                  # Changelog — v0.2 structured logging + request ID


```

---

## How to Run Locally

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.


---

## How to Run Tests

```bash
# Full test suite (26 tests)
pytest -v

# Unit tests only (engine + strategy)
pytest tests/test_engine.py -v

# Integration tests only (HTTP layer)
pytest tests/test_api.py -v
```

Expected output: **26 passed, 0 failed**

---

## How to Call the Endpoints

### POST /recommendations

Submit a support ticket and receive ranked recommendations.

```bash
curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cannot log in",
    "description": "I reset my password but still get an error",
    "top_n": 3
  }' | python -m json.tool
  
```
or
``` bash
$body = @{                           


  title = "Cannot log in"

  description = "I reset my password but still get an error"

} | ConvertTo-Json

  

Invoke-RestMethod "http://localhost:8000/recommendations" -Method Post -ContentType "application/json" -Body $body |

  ConvertTo-Json -Depth 10
```

**Response:**
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

**Request fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Short summary of the issue (min 1 char) |
| `description` | string | yes | Detailed description (min 1 char) |
| `top_n` | integer | no | Number of recommendations to return (1–10, default: 3) |

---

### GET /health

Health check — returns `200 OK` when the service is running.

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok"}
```

---

### GET /metrics

Returns request telemetry tracked by the middleware.

```bash
curl http://localhost:8000/metrics | python -m json.tool
```

```json
{
    "request_count": 5,
    "error_count": 1,
    "total_latency_ms": 18.42
}
```

---

## Validation Errors (422)

Invalid payloads return structured 422 responses:

```bash
# Empty title
curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"title": "", "description": "test"}' | python -m json.tool
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

---

## Determinism Verification

Same input always produces identical output:

```bash
R1=$(curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"title":"Cannot log in","description":"password reset error"}')

R2=$(curl -s -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"title":"Cannot log in","description":"password reset error"}')

[ "$R1" = "$R2" ] && echo "PASS deterministic" || echo "FAIL non-deterministic"
```

---
