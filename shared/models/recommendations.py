from typing import Optional

from beanie import Document
from pydantic import BaseModel, Field

from shared.schemas.recommendations import RecommendationSchema


class RecommendationModel(Document, RecommendationSchema):

    class Settings:
        name = "recommendations"


class RecommendationResponseModel(BaseModel):
    uid: str
    country: str
    season: str
    status: str
    recommendations: Optional[list] = Field(default_factory=list)


class RecommendationStatusResponseModel(BaseModel):
    uid: str
    status: str
    message: str = "No additional information available"
