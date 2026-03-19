"""Triage engine — delegates to the configured scoring strategy."""

from app.models import Recommendation
from app.rules.config import get_rule
from app.rules.keyword import CATEGORIES


def get_recommendations(
    title: str,
    description: str,
    top_n: int = 3,
) -> list[Recommendation]:
    """Return ranked recommendations. Same input → same output."""
    rule = get_rule()
    return rule.recommend(title=title, description=description, top_n=top_n)


def get_categories() -> list[str]:
    """Return the supported ticket category keys."""
    return [c["key"] for c in CATEGORIES]
