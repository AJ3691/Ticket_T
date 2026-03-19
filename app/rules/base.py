from abc import ABC, abstractmethod

from app.models import Recommendation


class TriageStrategy(ABC):
    """Base contract for all recommendation strategies."""

    @abstractmethod
    def recommend(self, title: str, description: str, top_n: int = 3) -> list[Recommendation]:
        """Return ranked recommendations for a support ticket.

        Args:
            title: Short summary of the issue
            description: Detailed description of the issue
            top_n: Maximum number of recommendations to return

        Returns:
            List of Recommendation objects, sorted by confidence descending
        """
        ...
