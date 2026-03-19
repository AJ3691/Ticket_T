from pydantic import BaseModel, Field


class TicketInput(BaseModel):
    """Incoming request model for ticket triage."""

    title: str = Field(..., min_length=1, description="Short summary of the issue")
    description: str = Field(..., min_length=1, description="Detailed description of the issue")
    top_n: int = Field(default=3, ge=1, le=10, description="Number of recommendations to return")


class Recommendation(BaseModel):
    """Single ranked recommendation result."""

    action: str = Field(..., description="Short recommended next action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    why: str = Field(..., description="1-2 sentence explanation for the recommendation")


class TriageResponse(BaseModel):
    """Response wrapper containing ranked recommendations."""

    recommendations: list[Recommendation]
