import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app_backend.producers.abstract_producer import AbstractProducer
from pycountry.db import Country
from pymongo.errors import PyMongoError

from shared.errors.backend_errors import CreateRecommendationError, UIDNotFoundError
from shared.errors.producer_errors import ProducerError
from shared.errors.repository_errors import RepositoryError
from shared.models.recommendations_requests import RecommendationRequest
from shared.repositories.abstract_repository import RecommendationBaseRepository
from shared.utils.country_utils import retrieve_existing_countries
from shared.utils.logger_utils import LoggerConfigurator
from shared.utils.singleton import Singleton

logger = LoggerConfigurator(name="recommendation-service").configure()

# Supported seasons
SUPPORTED_SEASONS = {"winter", "spring", "summer", "fall", "autumn"}


class RecommendationService(metaclass=Singleton):
    repository: Optional[RecommendationBaseRepository] = None
    producer: Optional[AbstractProducer] = None

    def __init__(
        self,
        repository: Optional[RecommendationBaseRepository] = None,
        producer: Optional[AbstractProducer] = None,
    ):
        self.repository = repository
        self.producer = producer

    def set_repository(
        self,
        repository: RecommendationBaseRepository,
    ) -> None:
        self.repository = repository

    def set_producer(
        self,
        producer: AbstractProducer,
    ) -> None:
        self.producer = producer

    def __str__(self):
        return f"RecommendationService(repository: {self.repository}, producer: {self.producer})s"

    async def country_validator(self, country: str) -> str:
        existing_countries: List[Country] = retrieve_existing_countries(country)
        logger.info(f"Country '{country}' found: {existing_countries}")
        if not existing_countries:
            raise CreateRecommendationError(f"Country '{country}' is not found.")

        countries: Dict[str, Country] = {
            country.name.lower(): country for country in existing_countries
        }
        if len(existing_countries) == 1:
            country_fuzzy_name = existing_countries[0].name
        elif country.lower() in countries:
            country_fuzzy_name = countries[country.lower()].name
        else:
            country_names = map(lambda c: c.name, existing_countries)
            raise CreateRecommendationError(
                f"Country '{country}' not found. Similar countries found: {', '.join(country_names)}. "
                "Please select the correct country."
            )
        return country_fuzzy_name

    async def create_recommendation(
        self,
        request: RecommendationRequest,
    ) -> str:
        """Creates a recommendation, writes it to repository, and sends it to producer."""
        # Validate country
        country_fuzzy_name = await self.country_validator(request.country)

        # Validate season
        if request.season not in SUPPORTED_SEASONS:
            raise CreateRecommendationError(
                f"Season '{request.season}' is not supported."
            )

        # Generate UID
        uid = str(uuid.uuid4())
        logger.info(f"Generating UID {uid} for {request.country} in {request.season}")
        recommendation_data = {
            "uid": uid,
            "country": request.country,
            "season": request.season,
            "status": "pending",
            "recommendations": [],
            "timestamp": datetime.utcnow(),
            "country_fuzzy_name": country_fuzzy_name,
        }

        # Store recommendation to MongoDB
        if self.repository is None:
            raise RepositoryError("Repository not set")
        try:
            recommendation = await self.repository.insert_one(recommendation_data)
        except Exception as e:
            logger.error(f"Failed to store recommendation: {e}")
            raise RepositoryError("Failed to store recommendation") from e

        if not recommendation:
            logger.error("Failed to store recommendation")
            raise PyMongoError("Failed to store recommendation")

        # Send recommendation to producer
        if self.producer is None:
            raise ProducerError("Producer not set")
        try:
            await self.producer.send_and_wait("recommendations", uid)
        except Exception as pe:
            logger.error(f"Failed to send recommendation: {pe}")
            raise ProducerError("Failed to send recommendation") from pe

        logger.info(
            f"Created recommendation request with UID {uid} for {request.country} in {request.season}"
        )
        return uid

    async def get_recommendation(self, uid: str) -> dict:
        if self.repository is None:
            raise RepositoryError("Repository not set")
        try:
            logger.info(f"Retrieving recommendation for UID {uid}")
            recommendation = await self.repository.find_one(filter_dict={"uid": uid})
        except Exception as e:
            logger.error(f"Error retrieving recommendation: {e}")
            raise RepositoryError("Error retrieving recommendation")
        else:
            if not recommendation or recommendation["status"] != "completed":
                logger.warning(f"Recommendation info with UID {uid} not found")
                raise UIDNotFoundError()
        logger.info(f"Retrieved recommendation for UID {uid}")
        return recommendation

    async def get_recommendation_status(self, uid: str) -> dict:
        if self.repository is None:
            raise RepositoryError("Repository not set")
        try:
            logger.info(f"Retrieving recommendation status for UID {uid}")
            recommendation = await self.repository.find_one(
                filter_dict={"uid": uid},
            )
        except Exception as e:
            logger.error(f"Error retrieving recommendation status: {e}")
            raise RepositoryError("Error retrieving recommendation")
        else:
            if not recommendation:
                logger.warning(f"Recommendation with UID {uid} not found")
                raise UIDNotFoundError()
            elif recommendation["status"] == "pending":
                logger.info(f"Recommendation with UID {uid} is still pending")
                recommendation = {
                    "uid": uid,
                    "status": "pending",
                    "message": "The recommendations are not yet available. Please try again later.",
                }
            elif recommendation["status"] == "error":
                logger.error(
                    f"Error occurred while processing recommendation with UID {uid}"
                )
                recommendation = {
                    "uid": uid,
                    "status": "error",
                    "message": "An error occurred while processing your request. Please try again later.",
                }
        logger.info(f"Retrieved recommendation for UID {uid}")
        return recommendation
