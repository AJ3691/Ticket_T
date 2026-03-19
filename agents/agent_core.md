# Core Agent

> **Version:** 1.0  |  **Phase:** 2  |  **Concurrency:** parallel (runs alongside API Agent)

---

## Mission

Own the recommendation engine, keyword strategy, and strategy configuration — producing deterministic, ranked recommendations through a modular strategy interface.

---

## Task Prompt

**→ [`prompts/create_core.md`](../prompts/create_core.md)**

Contains the exact spec for `app/engine.py`, `app/rules/keyword.py`, and `app/rules/config.py`: category definitions, scoring algorithm, deterministic tie-breaking, and all verification commands. Feed it to the agent alongside this file.


---

## Ownership Boundary

### Owned Files (read-write)

| File | Purpose |
|------|---------|
| `app/engine.py` | Entry point — `get_recommendations()` delegates to active strategy |
| `app/rules/keyword.py` | Concrete keyword-matching strategy implementation |
| `app/rules/config.py` | Strategy selector — returns the active `TriageStrategy` |

### Read-Only Dependencies

| File | Why needed |
|------|------------|
| `app/models.py` | Import `Recommendation` (frozen — do not modify) |
| `app/rules/base.py` | Import `TriageStrategy` abstract class (frozen — do not modify) |

### No-Touch Files

- `app/models.py` — frozen after Phase 1
- `app/rules/base.py` — frozen after Phase 1
- `app/main.py` — owned by API Agent
- `tests/` — owned by Test Agent

---

## Responsibilities

1. Implement `get_recommendations(title, description, top_n)` in `engine.py` as the single entry point
2. Implement `KeywordStrategy` in `keyword.py` — deterministic keyword matching with category-based scoring
3. Implement `get_rule()` in `config.py` — returns the active strategy instance
4. Ensure deterministic output: same input → identical recommendations every time
5. Sort results by confidence descending with stable tie-breaking
6. Respect `top_n` parameter — return at most `top_n` results

---

## Shared Contract

### Consumed Contracts

| Contract | Source | Shape |
|----------|--------|-------|
| `Recommendation` | `app/models.py` | `action: str, confidence: float [0-1], why: str` |
| `TriageStrategy` | `app/rules/base.py` | Abstract: `recommend(title, description, top_n) → list[Recommendation]` |

### Produced Contracts

| Contract | Consumers | Shape |
|----------|-----------|-------|
| `get_recommendations()` | API Agent (`main.py`), Test Agent | `(title: str, description: str, top_n: int = 3) → list[Recommendation]` |
| `KeywordStrategy` | `config.py`, Test Agent | Concrete `TriageStrategy` implementation |
| `get_rule()` | `engine.py` | `() → TriageStrategy` |

---

## Constraints

- **Deterministic:** No randomness, no timestamps, no external state in scoring
- **No HTTP concerns:** Do not import FastAPI or any HTTP library
- **No network calls:** Strategy must work entirely offline
- **No secrets:** No API keys or environment variables for core logic
- **Sorted output:** Results must be sorted by confidence descending
- **Stable tie-breaking:** Ties broken by fixed category order (alphabetical by category key)
- **Valid confidence:** All confidence values must be in [0.0, 1.0]
- **Modular:** Strategy interface allows swapping implementations without route changes

---

## Failure Protocol

| Blocker | Action |
|---------|--------|
| `Recommendation` model missing fields | STOP → report to orchestrator, do not modify `models.py` |
| `TriageStrategy` interface doesn't match expected signature | STOP → report contract gap |
| Need to add a field to the response | STOP → document requirement for Schema Agent |
| Test expectations conflict with implementation | STOP → report mismatch, do not modify tests |

**Rule:** Never make speculative edits across ownership boundaries. Report and wait.

---

## Definition of Done

- [ ] `app/engine.py` compiles without errors
- [ ] `app/rules/keyword.py` compiles without errors
- [ ] `app/rules/config.py` compiles without errors
- [ ] `get_recommendations()` returns `list[Recommendation]`
- [ ] Same input → identical output (determinism verified with 2+ calls)
- [ ] Results sorted by confidence descending
- [ ] `top_n` respected — never returns more than requested
- [ ] Unknown/unmatched input returns a valid list (may be empty or fallback)
- [ ] All confidence values in [0.0, 1.0]
- [ ] All action/why strings are non-empty
- [ ] No TODO/FIXME introduced
- [ ] No HTTP imports in core layer

---

## Execution Notes

**Pre-conditions:** Phase 1 complete — `app/models.py` and `app/rules/base.py` exist and are frozen
**Post-conditions:** `engine.py`, `keyword.py`, `config.py` compile and produce deterministic recommendations
**Handoff:** After both API and Core agents finish, run the Phase 2 Integration Check from `AGENTS.md`
