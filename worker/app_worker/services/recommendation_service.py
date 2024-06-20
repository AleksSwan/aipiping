from asyncio import Semaphore
from datetime import datetime

from app_worker.services.groq_service import GroqService

from shared.repositories.abstract_repository import RecommendationBaseRepository
from shared.utils.logger_utils import LoggerConfigurator

# Configure the logger
logger = LoggerConfigurator(name="recommendation-service").configure()


class RecommendationService:

    def __init__(
        self,
        db_recommendations: RecommendationBaseRepository,
        groq_service: GroqService,
    ):
        self.db_recommendations = db_recommendations
        self.groq_service = groq_service

    async def process_recommendation(
        self,
        uid: str,
        semaphore: Semaphore,
    ):
        """
        Process a single recommendation request by generating recommendations and updating the database.

        :param uid: The unique identifier for the recommendation request.
        :param db_recommendations: The repository to interact with the recommendations database.
        """
        async with semaphore:  # Acquire semaphore before processing
            try:
                recommendation = await self.db_recommendations.find_one(
                    filter_dict={"uid": uid}
                )
                if not recommendation:
                    logger.error(
                        f"Recommendation with UID {uid} not found in database."
                    )
                    return

                # Generate recommendations
                logger.info(f"Processing recommendation for UID {uid}")
                season = recommendation.get("season")
                country_fuzzy_name = recommendation.get("country_fuzzy_name")
                prompt = (
                    f"Give three things to do in {country_fuzzy_name} during {season}"
                )

                recommendations = await self.groq_service.generate_recommendations(
                    prompt
                )

                # Calculate processing time
                request_time = recommendation.get("timestamp")
                processing_time = datetime.utcnow() - request_time

                # Update recommendation in the database
                await self.db_recommendations.update_one(
                    {"uid": uid},
                    {
                        "$set": {
                            "status": "completed",
                            "recommendations": list(recommendations.values()),
                            "processing_time": processing_time.total_seconds(),
                        }
                    },
                )
                logger.info(f"Successfully generated recommendation for UID {uid}")
            except Exception as e:
                logger.error(f"Error processing recommendation for UID {uid}: {e}")
                try:
                    await self.db_recommendations.update_one(
                        {"uid": uid},
                        {
                            "$set": {
                                "status": "error",
                                "recommendations": [],
                                "error": str(e),
                            }
                        },
                    )
                except Exception as e:
                    logger.error(
                        f"Error updating info about processing error for UID {uid}: {e}"
                    )
