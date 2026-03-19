

```bash
# Phase 3 build — create full test suite
claude "Read agents/agent_tests.md and prompts/create_tests.md. Execute the task. Create all files specified. Run all verification commands. Report results."

# Ad-hoc — add specific tests later
claude "Read agents/agent_tests.md and prompts/add_tests.md. Add tests for [behavior]. Run verification. Report results."
```

### Manual verification after any test task
```bash
pytest -v
```
