# {Agent Name} Agent

> **Version:** {x.y}  |  **Phase:** {1|2|3}  |  **Concurrency:** {solo|parallel}

---

## Mission

{One sentence. What this agent exists to do and why it matters to the system.}

---

## Task Prompt

**→ [`prompts/{task_name}.md`](../prompts/{task_name}.md)**

{One line: what the linked prompt tells this agent to do. Feed it to the agent alongside this file.}

---

## How to Run This Agent

### Using Claude Code
```bash
claude "Read agents/{agent_name}.md and prompts/{task_name}.md. Execute the task. Create all files specified. Run all verification commands. Report results."
```

### Manual verification after agent finishes
```bash
{verification commands}
```

---

## Ownership Boundary

### Owned Files (read-write)

| File | Purpose |
|------|---------|
| `{path}` | {what it contains} |

### Read-Only Dependencies

| File | Why needed |
|------|------------|
| `{path}` | {what this agent reads from it} |

### No-Touch Files

{List files this agent must never modify, even if blocked.}

---

## Responsibilities

1. {Primary responsibility}
2. {Secondary responsibility}
3. {Tertiary responsibility}

---

## Shared Contract

### Consumed Contracts

| Contract | Source | Shape |
|----------|--------|-------|
| `{interface/model}` | `{file}` | `{signature or schema}` |

### Produced Contracts

| Contract | Consumers | Shape |
|----------|-----------|-------|
| `{interface/model}` | `{who uses it}` | `{signature or schema}` |

---

## Constraints

- {Hard constraint 1}
- {Hard constraint 2}
- {Hard constraint 3}

---

## Failure Protocol

| Blocker | Action |
|---------|--------|
| {Scenario 1} | STOP → report dependency to orchestrator |
| {Scenario 2} | STOP → document contract gap |
| {Scenario 3} | STOP → request cross-agent coordination |

**Rule:** Never make speculative edits across ownership boundaries. Report and wait.

---

## Definition of Done

- [ ] Owned files compile without errors
- [ ] Shared contracts remain unchanged (or change is explicitly approved)
- [ ] All tests pass
- [ ] No TODO/FIXME introduced
- [ ] Deterministic behavior preserved
- [ ] {Agent-specific done criterion}

---

## Execution Notes

**Pre-conditions:** {What must be true before this agent starts}
**Post-conditions:** {What must be true after this agent finishes}
**Handoff:** {What artifact or signal tells the next phase it can begin}
gg