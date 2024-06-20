from typing import Optional

from beanie import Document
from pydantic import BaseModel, Field

from shared.schemas.recommendations import RecommendationSchema


class RecommendationModel(Document, RecommendationSchema):

    class Settings:
        name = "recommendations"


class RecommendationResponseModel(BaseModel):
    uid: Optional[str]
    country: Optional[str] = None
    season: Optional[str] = None
    status: Optional[str]
    recommendations: Optional[list] = Field(default_factory=list)
    error: Optional[str] = None
    message: Optional[str] = None
