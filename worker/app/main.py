import asyncio
from asyncio import Semaphore

from aiokafka import AIOKafkaConsumer  # type: ignore
from aiokafka.errors import KafkaConnectionError, KafkaError  # type: ignore
from app.consumers.kafka_consumer import consume
from app.services.groq_service import GroqService
from app.services.recommendation_service import RecommendationService

from shared.exceptions.custom_exeptions import DatabaseConnectionError
from shared.repositories.recoomendations import (
    MongoRepository,
    RecommendationBaseRepository,
)
from shared.utils.logger_configurator import LoggerConfigurator

# Configure the logger
logger = LoggerConfigurator(name=__name__, log_file="worker.log").configure()


db_recommendations = MongoRepository(
    db_uri="mongodb://mongodb:27017",
    db_name="travel_recommendations",
)

groq_service = GroqService()

recommendator = RecommendationService(
    db_recommendations=db_recommendations,
    groq_service=groq_service,
)


def get_consumer():
    return AIOKafkaConsumer(
        "recommendations",
        bootstrap_servers="kafka:9092",
        group_id="recommendation_group",
    )


async def main(
    db_recommendations: RecommendationBaseRepository,
    kafka_consumer: AIOKafkaConsumer,
    groq_service: GroqService,
    recommendator: RecommendationService,
    limit_errors: int = 5,
):
    """
    Main function to start the Kafka consumer and handle errors.
    """
    # Semaphore to limit concurrent requests
    semaphore: Semaphore = Semaphore(5)  # Adjust the value as needed

    # Initialize database
    logger.info("Starting worker")

    logger.info("Initializing database")
    try:
        await db_recommendations.initialize()
        logger.info("Database initialized successfully")
    except DatabaseConnectionError as e:
        logger.error(f"Error occurred while trying to connect to MongoDB: {e}")
        return

    consumer = kafka_consumer()

    logger.info(f"Starting worker with limit_errors = {limit_errors}")
    error_count = 0

    while True and error_count < limit_errors:
        try:
            await consume(
                db_recommendations=db_recommendations,
                consumer=consumer,
                groq_service=groq_service,
                recommendation_service=recommendator,
                semaphore=semaphore,
            )
        except KafkaConnectionError as e:
            error_count += 1
            logger.error(f"Failed to connect to Kafka: {e}")
        except KafkaError as e:
            error_count += 1
            logger.error(f"Failed to consume from Kafka: {e}")
        except Exception as e:
            error_count += 1
            logger.error(f"Error in consumer: {e}")

    logger.info("Exiting worker")
    return error_count


if __name__ == "__main__":
    asyncio.run(
        main(
            db_recommendations=db_recommendations,
            kafka_consumer=get_consumer,
            groq_service=groq_service,
            recommendator=recommendator,
        )
    )
