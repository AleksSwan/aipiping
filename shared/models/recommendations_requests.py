from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """Data model for a recommendation request."""

    country: str = Field()
    season: str = Field()
