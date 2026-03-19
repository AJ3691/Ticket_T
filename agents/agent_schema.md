# Schema Agent

> **Version:** 1.2  |  **Phase:** 1  |  **Concurrency:** solo (runs before parallel phase)

---

## Mission

Define and freeze the shared data contracts (request models, response models, strategy interface) so that API and Core agents can work in parallel without contract drift.

---

## Task Prompt

**→ [`prompts/create_schema.md`](../prompts/create_schema.md)**

This is the executable task. It contains the exact spec, file-by-file instructions, constraints, and verification commands. Feed it to the agent alongside this file.

---

## Ownership Boundary

### Owned Files (read-write)

| File | Purpose |
|------|---------|
| `app/models.py` | Pydantic models — TicketInput, Recommendation, TriageResponse |
| `app/rules/base.py` | Abstract strategy interface — TriageStrategy protocol |
| `app/__init__.py` | Package init |
| `app/rules/__init__.py` | Package init |
| `requirements.txt` | Project dependencies |

### Read-Only Dependencies

| File | Why needed |
|------|------------|
| `docs/api.md` | Verify models match documented endpoint contract |

### No-Touch Files

- `app/main.py` — owned by API Agent
- `app/engine.py` — owned by Core Agent
- `app/rules/keyword.py` — owned by Core Agent
- `app/rules/config.py` — owned by Core Agent
- `tests/` — owned by Test Agent

---

## Responsibilities

1. Define request/response Pydantic models with strict validation (min_length, ge/le bounds, required fields)
2. Define the `TriageStrategy` abstract interface that all recommendation strategies must implement
3. Ensure models serialize cleanly to JSON and match the documented API contract
4. Freeze contracts before Phase 2 begins — no silent changes after handoff

---

## Shared Contract

### Consumed Contracts

| Contract | Source | Shape |
|----------|--------|-------|
| API spec | `docs/api.md` | Endpoint shape, field names, example payloads |

### Produced Contracts

| Contract | Consumers | Shape |
|----------|-----------|-------|
| `TicketInput` | API Agent (`main.py`) | `title: str, description: str, top_n: int = 3` |
| `Recommendation` | Core Agent (`engine.py`, `keyword.py`) | `action: str, confidence: float [0-1], why: str` |
| `TriageResponse` | API Agent (`main.py`) | `recommendations: list[Recommendation]` |
| `TriageStrategy` | Core Agent (`base.py`, `keyword.py`, `config.py`) | `recommend(title, description, top_n) -> list[Recommendation]` |

---

## Constraints

- Models must use Pydantic v2 `BaseModel` with `Field` validators
- `confidence` must be bounded `ge=0.0, le=1.0`
- `title` and `description` must enforce `min_length=1` (no empty strings)
- `top_n` must default to `3`, bounded `ge=1, le=10`
- No business logic in models — models define shape, not behavior
- No external dependencies beyond Pydantic and stdlib
- Strategy interface must be abstract — no concrete implementation in `base.py`

---

## Failure Protocol

| Blocker | Action |
|---------|--------|
| API doc conflicts with model shape | STOP -> flag to orchestrator, propose resolution |
| Core agent needs a field not in the model | STOP -> document the gap, do not add speculatively |
| Pydantic version incompatibility | STOP -> report version constraint |

**Rule:** Never make speculative edits across ownership boundaries. Report and wait.

---

## Definition of Done

- [ ] `app/models.py` compiles without errors
- [ ] `app/rules/base.py` compiles without errors
- [ ] All Pydantic models have correct Field validators
- [ ] `TriageStrategy` interface defines `recommend()` with correct signature
- [ ] Models serialize/deserialize correctly (round-trip test)
- [ ] Validation rejects: empty title, empty description, confidence > 1.0, top_n = 0
- [ ] No TODO/FIXME introduced
- [ ] Contracts are frozen — ready for Phase 2 handoff

---

## Execution Notes

**Pre-conditions:** Repo root exists, Python 3.11+ available
**Post-conditions:** `models.py` and `base.py` are stable, importable, and frozen
**Handoff:** After Schema Agent completes and all verification passes, commit with message `"schema: freeze shared contracts for Phase 2"`. API Agent and Core Agent may now begin parallel work.

---

## Expected Schema (reference)

### TicketInput
```python
class TicketInput(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    top_n: int = Field(default=3, ge=1, le=10)
```

### Recommendation
```python
class Recommendation(BaseModel):
    action: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    why: str
```

### TriageResponse
```python
class TriageResponse(BaseModel):
    recommendations: list[Recommendation]
```

### TriageStrategy (abstract)
```python
class TriageStrategy(ABC):
    @abstractmethod
    def recommend(self, title: str, description: str, top_n: int = 3) -> list[Recommendation]:
        ...
```
