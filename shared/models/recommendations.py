from beanie import Document

from shared.schemas.recommendations import RecommendationSchema


class Recommendation(Document, RecommendationSchema):

    class Settings:
        name = "recommendations"
