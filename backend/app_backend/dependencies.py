from app_backend.producers.abstract_producer import AbstractProducer
from app_backend.producers.kafka_producer import KafkaProducer
from app_backend.services.recommendation_service import RecommendationService

from shared.errors.producer_errors import ProducerError
from shared.errors.repository_errors import DatabaseConnectionError
from shared.repositories.abstract_repository import RecommendationBaseRepository
from shared.repositories.mongo_repository import MongoRepository
from shared.utils.logger_utils import LoggerConfigurator

logger = LoggerConfigurator(name="app-backend-dependencies").configure()


# MongoDB setup
async def get_db() -> RecommendationBaseRepository:
    logger.debug("Repository requested")
    try:
        db_recommendations: RecommendationBaseRepository = MongoRepository(
            db_uri="mongodb://mongodb:27017",
            db_name="travel_recommendations",
        )
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise DatabaseConnectionError("Cannot initialize database") from e
    return db_recommendations


# Producer setup
async def get_producer() -> AbstractProducer:
    logger.debug("Producer requested")
    try:
        producer: AbstractProducer = KafkaProducer(bootstrap_servers="kafka:9092")
    except Exception as e:
        logger.error(f"Producer initialization failed: {e}")
        raise ProducerError("Cannot initialize producer") from e
    return producer


# Recommendation service
async def get_recommendation_service() -> RecommendationService:
    logger.debug("Recommendation service requested")
    recommendation_service: RecommendationService = RecommendationService()
    return recommendation_service
