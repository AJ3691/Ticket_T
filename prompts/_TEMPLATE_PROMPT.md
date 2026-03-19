# Task: {Task Title}

> **Target Agent:** {agent_schema | agent_api | agent_core | agent_tests}
> **Phase:** {1|2|3}  |  **Priority:** {P0|P1|P2}  |  **Estimated Scope:** {small|medium|large}

---

## Goal

{One sentence. What this task accomplishes and why it matters right now.}

---

## Context

### Current State
- {What exists today that this task builds on or modifies}

### Trigger
- {Why this task is being run — what changed or what's needed}

---

## Inputs

| Input | Location | Status |
|-------|----------|--------|
| `{file or artifact}` | `{path}` | {exists | must-be-created | frozen} |

---

## Expected Output

| Output | Location | Shape |
|--------|----------|-------|
| `{file or artifact}` | `{path}` | {description of what it should contain} |

---

## Constraints

- {Constraint 1 — e.g., do not modify files outside ownership boundary}
- {Constraint 2 — e.g., preserve deterministic behavior}
- {Constraint 3 — e.g., no external dependencies}

---

## Process

1. {Step 1 — inspect/read}
2. {Step 2 — plan the change}
3. {Step 3 — implement}
4. {Step 4 — verify locally}
5. {Step 5 — run tests}

---

## No-Touch Boundaries

| File/Dir | Reason |
|----------|--------|
| `{path}` | {why this must not be modified in this task} |

---

## Verification

```bash
# Minimum verification
{command}

# Full verification
pytest -v
```

---

## Deliverable Summary

Return:
- Files changed: {list}
- What changed: {summary}
- Contract impact: {none | describe}
- Tests affected: {none | describe}

---

## Rollback Signal

If this task produces incorrect output:
- {What to revert}
- {How to know it failed}
- {Who/what to notify}
