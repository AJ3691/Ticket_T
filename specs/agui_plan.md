# AG-UI Integration — Master Plan
# Support Ticket Triage — Agent Runner with AG-UI Protocol

---

## Summary

Add AG-UI (Agent-User Interaction Protocol) to the existing agent runner so
agent executions can be observed in real time from a browser. Three phases,
each independently shippable.

## Phase Overview

| Phase | Spec File | Goal | Key Deliverables |
|-------|-----------|------|-----------------|
| 1 | `specs/agui_phase1.md` | Wire AG-UI backend | `agui_server.py`, `agent_runner/agui_adapter.py` |
| 2 | `specs/agui_phase2.md` | Minimal React frontend | `agui-frontend/` — React app consuming SSE |
| 3 | `specs/agui_phase3.md` | Direct LLM streaming service | `agent_runner/llm_adapter.py`, new endpoint |

## Dependency Chain

```
Phase 1 (backend SSE)
    │
    ▼
Phase 2 (React frontend) ← needs Phase 1 running
    │
    ▼
Phase 3 (LLM service) ← needs Phase 1 endpoint pattern, Phase 2 UI
```

Phase 1 must be complete and verified before Phase 2 starts.
Phase 2 must be complete before Phase 3 (so we can see the LLM output in the UI).

## Handoff Workflow

Each phase follows the same pattern:

1. **Read the spec** — the spec file is the complete contract
2. **Read existing code** — files listed in "Context for the implementing agent"
3. **Build** — create only the files listed
4. **Test** — run every verification command in the acceptance criteria
5. **Document** — update `docs/agui.md` with what was built (append, don't overwrite)

### How to invoke

```bash
cd "C:\Users\Mindrix\Documents\Projects\Opus 4.6"

# Phase 1
claude "Read specs/agui_phase1.md. Implement everything described. Run all verification commands. Update docs/agui.md with what you built."

# Phase 2 (after Phase 1 is verified)
claude "Read specs/agui_phase2.md. Implement everything described. Run all verification commands. Append to docs/agui.md."

# Phase 3 (after Phase 2 is verified)
claude "Read specs/agui_phase3.md. Implement everything described. Run all verification commands. Append to docs/agui.md."
```

## Documentation Requirement

Every phase must append to `docs/agui.md` with:

1. **What was built** — files created/modified, one line each
2. **How to run it** — exact commands
3. **Architecture decisions** — why this approach, what was considered
4. **What's next** — pointer to the next phase spec

This creates a running log of the AG-UI integration that accumulates across phases.

## Test Strategy

Each phase has three levels of testing:

1. **Import tests** — verify new modules import without errors
2. **Unit/integration tests** — `tests/test_agui_*.py` files
3. **Manual smoke tests** — curl commands or browser checks with expected output

The implementing agent must run ALL verification commands and report results.
If any test fails, fix it before marking the phase complete.
