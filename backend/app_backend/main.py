from contextlib import asynccontextmanager

import uvicorn
from app_backend.dependencies import get_db, get_producer, get_recommendation_service
from app_backend.producers.abstract_producer import AbstractProducer
from app_backend.routes.recommendations import router as RecommendationRouter
from app_backend.services.recommendation_service import RecommendationService
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.errors.producer_errors import ProducerStartError
from shared.errors.repository_errors import DatabaseConnectionError
from shared.middlewares.recommendation_middlewares import ExceptionMiddleware
from shared.repositories.abstract_repository import RecommendationBaseRepository
from shared.utils.logger_utils import LoggerConfigurator

# Configure the logger
logger = LoggerConfigurator(name="app-backend", log_file="app-backend.log").configure()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """
    Lifespan management for the FastAPI application.
    Ensures the producer is started and stopped with the application.
    Ensures the database is connected on start the application.
    """

    logger.info("Lifespan startup...")
    logger.info("Initializing database")
    db_recommendations: RecommendationBaseRepository = await get_db()
    try:
        await db_recommendations.initialize()
        logger.info("Database initialized successfully")
    except DatabaseConnectionError as e:
        logger.error(f"Error occurred while trying to connect to repository: {e}")
        raise ProducerStartError("Error occurred while trying to connect to repository")

    producer: AbstractProducer = await get_producer()
    if not producer:
        logger.info("Producer not setup")
        raise ProducerStartError("Producer initialization failed")
    try:
        await producer.start()
    except ProducerStartError:
        logger.error("Producer initialization failed")
        raise ProducerStartError("Producer initialization failed")
    logger.info("Producer started")

    # Recommendation service
    logger.info("Initializing recommendation service")
    recommendation_service: RecommendationService = await get_recommendation_service()
    recommendation_service.set_repository(repository=db_recommendations)
    recommendation_service.set_producer(producer=producer)
    logger.info("Recommendation service initialized")

    logger.info("Lifespan startup complete")

    yield

    logger.info("Lifespan shutdown...")
    logger.info("Stopping producer and database connections")
    if recommendation_service.producer:
        try:
            await recommendation_service.producer.stop()
        except Exception as e:
            logger.error(f"Producer shutdown failed: {e}")
        else:
            logger.info("Producer stopped")
    if recommendation_service.repository:
        try:
            await recommendation_service.repository.disconnect()
        except Exception as e:
            logger.error(f"Database shutdown failed: {e}")
        else:
            logger.info("Database disconnected")
    logger.info("Lifespan shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="TO DO recommendations server",
    description="Recommend three things to do in a given country during a specific season by consulting the LLM",
    version="0.2.12",
    contact={
        "name": "Aleks",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan,
)

logger.info("Append routes")
app.include_router(
    RecommendationRouter,
    prefix="/recommendations",
)

logger.info("Append middlewares")
app.add_middleware(ExceptionMiddleware)

# Allow CORS requests from the front-end
origins = [
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    # Run the FastAPI application with Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
