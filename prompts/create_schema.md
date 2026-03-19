# Task: Create Shared Contracts

> **Target Agent:** agent_schema
> **Phase:** 1  |  **Priority:** P0  |  **Estimated Scope:** medium

---

## Goal

Create the frozen shared contracts (`app/models.py` and `app/rules/base.py`) that API and Core agents depend on. This must complete before any parallel work begins.

---

## Context

### Current State
- Fresh repo with no `app/` directory yet
- `requirements.txt` needs to be created with `fastapi`, `pydantic`, `uvicorn`, `pytest`, `httpx`
- `docs/api.md` defines the target endpoint contract

### Trigger
- Phase 1 kickoff — nothing else can start until contracts are frozen

---

## Inputs

| Input | Location | Status |
|-------|----------|--------|
| `docs/api.md` | `docs/api.md` | must-be-created (if not exists, use spec below) |
| `requirements.txt` | `requirements.txt` | must-be-created |

---

## Expected Output

| Output | Location | Shape |
|--------|----------|-------|
| `app/__init__.py` | `app/__init__.py` | Empty init file |
| `app/models.py` | `app/models.py` | Pydantic models: TicketInput, Recommendation, TriageResponse |
| `app/rules/__init__.py` | `app/rules/__init__.py` | Empty init file |
| `app/rules/base.py` | `app/rules/base.py` | Abstract TriageStrategy with `recommend()` method |
| `requirements.txt` | `requirements.txt` | Pinned dependencies |

---

## Spec: What to Create

### 1. `requirements.txt`
```
fastapi>=0.110.0
pydantic>=2.0.0
uvicorn>=0.29.0
pytest>=8.0.0
httpx>=0.27.0
```

### 2. `app/__init__.py`
Empty file.

### 3. `app/models.py`
Create three Pydantic v2 models:

**TicketInput** — incoming request:
- `title: str` — required, min_length=1, description="Short summary of the issue"
- `description: str` — required, min_length=1, description="Detailed description of the issue"
- `top_n: int` — default=3, ge=1, le=10, description="Number of recommendations to return"

**Recommendation** — single ranked result:
- `action: str` — short recommended next action
- `confidence: float` — ge=0.0, le=1.0, score
- `why: str` — 1-2 sentence explanation

**TriageResponse** — response wrapper:
- `recommendations: list[Recommendation]`

All models must use `BaseModel` and `Field` from Pydantic. Include docstrings.

### 4. `app/rules/__init__.py`
Empty file.

### 5. `app/rules/base.py`
Create an abstract base class:

```python
from abc import ABC, abstractmethod
from app.models import Recommendation

class TriageStrategy(ABC):
    """Base contract for all recommendation strategies."""

    @abstractmethod
    def recommend(self, title: str, description: str, top_n: int = 3) -> list[Recommendation]:
        """Return ranked recommendations for a support ticket.
        
        Args:
            title: Short summary of the issue
            description: Detailed description of the issue
            top_n: Maximum number of recommendations to return
            
        Returns:
            List of Recommendation objects, sorted by confidence descending
        """
        ...
```

---

## Constraints

- Do not create `main.py`, `engine.py`, `keyword.py`, or `config.py` — those belong to other agents
- Do not create any test files — owned by Test Agent
- No business logic in models — models define shape only
- No external dependencies beyond pydantic and stdlib
- Strategy interface must be abstract with no concrete implementation

---

## Process

1. Create directory structure: `app/`, `app/rules/`
2. Create `requirements.txt`
3. Create `app/__init__.py` (empty)
4. Create `app/models.py` with all three Pydantic models
5. Create `app/rules/__init__.py` (empty)
6. Create `app/rules/base.py` with abstract TriageStrategy
7. Run compile checks on both files
8. Run import validation
9. Run schema round-trip test

---

## No-Touch Boundaries

| File/Dir | Reason |
|----------|--------|
| `app/main.py` | Owned by API Agent — Phase 2 |
| `app/engine.py` | Owned by Core Agent — Phase 2 |
| `app/rules/keyword.py` | Owned by Core Agent — Phase 2 |
| `app/rules/config.py` | Owned by Core Agent — Phase 2 |
| `tests/` | Owned by Test Agent — Phase 3 |

---

## Verification

```bash
# Compile check
python -m py_compile app/models.py
python -m py_compile app/rules/base.py

# Import validation
python -c "from app.models import TicketInput, Recommendation, TriageResponse; print('Models OK')"
python -c "from app.rules.base import TriageStrategy; print('Strategy interface OK')"

# Schema round-trip test
python -c "
from app.models import TicketInput, Recommendation, TriageResponse
t = TicketInput(title='test', description='test desc')
r = Recommendation(action='do x', confidence=0.8, why='because')
resp = TriageResponse(recommendations=[r])
print(resp.model_dump_json(indent=2))
print('Round-trip OK')
"

# Validation edge cases
python -c "
from pydantic import ValidationError
from app.models import TicketInput, Recommendation

# Empty title should fail
try:
    TicketInput(title='', description='valid')
    print('FAIL: empty title accepted')
except ValidationError:
    print('PASS: empty title rejected')

# Confidence out of range should fail
try:
    Recommendation(action='x', confidence=1.5, why='y')
    print('FAIL: confidence > 1.0 accepted')
except ValidationError:
    print('PASS: confidence > 1.0 rejected')

# top_n out of range should fail
try:
    TicketInput(title='x', description='y', top_n=0)
    print('FAIL: top_n=0 accepted')
except ValidationError:
    print('PASS: top_n=0 rejected')
"
```

---

## Deliverable Summary

Return:
- Files created: `requirements.txt`, `app/__init__.py`, `app/models.py`, `app/rules/__init__.py`, `app/rules/base.py`
- What was created: Shared Pydantic contracts + abstract strategy interface
- Contract impact: This IS the contract — all other agents depend on it
- Tests affected: None yet — Test Agent runs in Phase 3

---

## Rollback Signal

If this task produces incorrect output:
- Delete `app/models.py` and `app/rules/base.py`, recreate from scratch
- Signal: compile check fails, round-trip fails, or validation edge cases fail
- Notify: Orchestrator — Phase 2 cannot begin until this passes
