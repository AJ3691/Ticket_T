"""Strategy selector — returns the active TriageStrategy."""

from app.rules.llm import LLMStrategy


def get_rule():
    """Return the active recommendation strategy."""
    return LLMStrategy()
