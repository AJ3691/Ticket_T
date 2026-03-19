# Architecture

## Overview

Support Ticket Triage is a FastAPI service that accepts a support ticket (title + description) and returns ranked, deterministic recommendations for how to handle it. It uses a keyword-matching strategy to score against 6 support categories and returns the top N results sorted by confidence.

---

## Module Map

```
app/
├── main.py          HTTP layer — routes, validation, telemetry middleware
├── engine.py        Orchestration — single entry point, delegates to strategy
├── models.py        Contracts — TicketInput, Recommendation, TriageResponse (frozen)
└── rules/
    ├── base.py      Abstract interface — TriageStrategy (frozen)
    ├── keyword.py   Concrete strategy — keyword scoring across 6 categories
    └── config.py    Strategy selector — returns the active TriageStrategy
```

---

## Request Flow

```
HTTP POST /recommendations
        │
        ▼
  [main.py] telemetry_middleware
  — records request_count, latency, error_count
        │
        ▼
  [main.py] recommend()
  — FastAPI validates TicketInput via Pydantic
  — delegates to engine, returns TriageResponse
        │
        ▼
  [engine.py] get_recommendations(title, description, top_n)
  — calls get_rule() to get active strategy
        │
        ▼
  [rules/config.py] get_rule()
  — returns KeywordStrategy()
        │
        ▼
  [rules/keyword.py] KeywordStrategy.recommend()
  — scores text against 6 categories
  — sorts by confidence desc, ties by category key asc
  — returns top_n Recommendation objects
        │
        ▼
  TriageResponse(recommendations=[...])  →  JSON response
```

---

## Key Interfaces

### Request — `TicketInput` (`app/models.py`)
```python
TicketInput(
    title: str,        # min_length=1
    description: str,  # min_length=1
    top_n: int = 3,    # ge=1, le=10
)
```

### Response — `TriageResponse` (`app/models.py`)
```python
TriageResponse(
    recommendations: list[Recommendation]
)

Recommendation(
    action: str,        # short recommended next step
    confidence: float,  # [0.0, 1.0] — higher = more relevant
    why: str,           # 1-2 sentence rationale
)
```

### Strategy Interface — `TriageStrategy` (`app/rules/base.py`)
```python
class TriageStrategy(ABC):
    def recommend(self, title: str, description: str, top_n: int = 3) -> list[Recommendation]:
        ...
```

### Engine Entry Point — `app/engine.py`
```python
get_recommendations(title: str, description: str, top_n: int = 3) -> list[Recommendation]
```

---

## Scoring Algorithm (`KeywordStrategy`)

1. Combine `title + " " + description`, lowercase
2. For each of 6 categories, count keyword matches
3. `confidence = round(min(matches / total_keywords * weight, 1.0), 2)`
4. Apply per-action decay: action 1 = full, action 2 = −15%, action 3 = −30%
5. Sort: confidence descending, ties broken by category key alphabetically
6. Return top_n; fallback to 3 default actions if zero categories match

**Categories:** `access`, `auth`, `billing`, `data`, `integration`, `performance`
**Weights:** auth (0.95) → access (0.90) → billing (0.85) → performance (0.80) → data (0.75) → integration (0.70)

---

## Telemetry

In-memory dict tracked by HTTP middleware on every request:

| Metric | Type | Description |
|--------|------|-------------|
| `request_count` | int | Total requests received |
| `error_count` | int | Responses with status ≥ 400 |
| `total_latency_ms` | float | Cumulative response time in ms |

Exposed at `GET /metrics`. Resets on server restart.

---

## Adding a New Strategy

1. Create `app/rules/{name}.py` implementing `TriageStrategy`
2. Update `app/rules/config.py` to return the new strategy — one line change
3. `app/engine.py` and `app/main.py` require zero changes
