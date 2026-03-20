"""
registry.py — Central map of agent names → system prompt files
                         and task names → instruction prompt files.

Adding a new agent:  drop a .md in agents/ and add one line here.
Adding a new task:   drop a .md in prompts/ and add one line here.
"""

AGENTS: dict[str, str] = {
    "schema": "agents/agent_schema.md",
    "api":    "agents/agent_api.md",
    "core":   "agents/agent_core.md",
    "test":   "agents/agent_tests.md",
}

TASKS: dict[str, str] = {
    "add_strategy":           "prompts/add_strategy.md",
    "add_endpoint":           "prompts/add_endpoint.md",
    "add_telemetry":          "prompts/add_telemetry.md",
    "add_tests":              "prompts/add_tests.md",
    "improve_error_handling": "prompts/improve_error_handling.md",
    "create_schema":          "prompts/create_schema.md",
    "create_api":             "prompts/create_api.md",
    "create_core":            "prompts/create_core.md",
    "create_tests":           "prompts/create_tests.md",
}


def resolve_agent(name: str) -> str:
    """Return the file path for an agent name, or raise ValueError."""
    if name not in AGENTS:
        known = ", ".join(sorted(AGENTS))
        raise ValueError(f"Unknown agent '{name}'. Known agents: {known}")
    return AGENTS[name]


def resolve_task(name: str) -> str:
    """Return the file path for a task name, or raise ValueError."""
    if name not in TASKS:
        known = ", ".join(sorted(TASKS))
        raise ValueError(f"Unknown task '{name}'. Known tasks: {known}")
    return TASKS[name]
