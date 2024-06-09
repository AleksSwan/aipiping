from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RecommendationSchema(BaseModel):
    uid: str
    country: str
    season: str
    country_fuzzy_name: str
    status: str
    recommendations: list
    timestamp: datetime
    processing_time: Optional[float] = None
    error: Optional[str] = None
