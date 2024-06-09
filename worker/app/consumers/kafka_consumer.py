from asyncio import Semaphore

from aiokafka import AIOKafkaConsumer  # type: ignore
from app.services.groq_service import GroqService
from app.services.recommendation_service import RecommendationService

from shared.repositories.recoomendations import RecommendationBaseRepository
from shared.utils.logger_configurator import LoggerConfigurator

logger = LoggerConfigurator(name="kafka_consumer").configure()


async def consume(
    db_recommendations: RecommendationBaseRepository,
    consumer: AIOKafkaConsumer,
    groq_service: GroqService,
    recommendation_service: RecommendationService,
    semaphore: Semaphore,
):
    """
    Consume messages from the Kafka topic and process recommendations.

    :param db_recommendations: The repository to interact with the recommendations database.
    """
    try:
        await consumer.start()
        async for msg in consumer:
            uid = msg.value.decode("utf-8")
            logger.info(f"Consumed recommendation for UID: {uid}")
            await recommendation_service.process_recommendation(
                uid=uid,
                semaphore=semaphore,
            )
            await consumer.commit()
    finally:
        await consumer.stop()
