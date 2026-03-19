"""Strategy selector — returns the active TriageStrategy."""

from app.rules.keyword import KeywordStrategy


def get_rule():
    """Return the active recommendation strategy."""
    return KeywordStrategy()
