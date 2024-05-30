import asyncio
import uuid
from datetime import datetime

import pycountry
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from errors import ProducerError
from logger_configurator import LoggerConfigurator
from producer import AbstractProducer, KafkaProducer
from repository import AbstractRecommendationRepository, MongoRepository

# Initialize FastAPI application
app = FastAPI()

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

# Configure the logger
logger = LoggerConfigurator(name=__name__, log_file="api.log").configure()

# MongoDB setup
db_recommendations = MongoRepository(
    uri="mongodb://mongodb:27017",
    db_name="travel_recommendations",
    collection_name="recommendations",
)

# Producer setup
try:
    producer: AbstractProducer = KafkaProducer(bootstrap_servers="kafka:9092")
except Exception as e:
    logger.error(f"Producer initialization failed: {e}")
    producer = None

# Supported seasons
SUPPORTED_SEASONS = {"winter", "spring", "summer", "fall", "autumn"}


class RecommendationRequest(BaseModel):
    """
    Data model for a recommendation request.
    """

    country: str = Field()
    season: str = Field()


class Lifespan:
    """
    Lifespan management for the FastAPI application.
    Ensures the producer is started and stopped with the application.
    """

    def __init__(self, app: FastAPI):
        self.app = app

    async def __aenter__(self):
        global producer
        if not producer:
            logger.info("Producer not initialized")
            return
        await producer.start()
        logger.info("Producer started")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        global producer
        await producer.stop()
        logger.info("Producer stopped")


app.router.lifespan_context = Lifespan


@app.post("/recommendations", status_code=202)
async def create_recommendation(request: RecommendationRequest):
    """
    Endpoint to create a recommendation request.

    :param request: RecommendationRequest object containing country and season.
    :return: JSON response with the generated UID.
    """
    try:
        # Validate country
        try:
            country = pycountry.countries.search_fuzzy(request.country)
            logger.info(f"Country '{request.country}' found: {country}")
        except LookupError:
            country = None
        if not country:
            raise HTTPException(
                status_code=400, detail=f"Country '{request.country}' is not found."
            )
        elif len(country) > 1:
            country_names = [c.name for c in country]
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Country '{request.country}' not found. Similar countries found: {', '.join(country_names)}. "
                    "Please select the correct country."
                ),
            )
        else:
            country = country[0].name

        # Validate season
        if request.season not in SUPPORTED_SEASONS:
            raise HTTPException(
                status_code=400, detail=f"Season '{request.season}' is not supported."
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
            "country_fuzzy_name": country,
        }

        # Store recommendation to MongoDB
        await db_recommendations.insert_one(recommendation_data)

        # Send recommendation to producer
        try:
            await producer.send_and_wait("recommendations", uid)
        except ProducerError as pe:
            logger.error(f"Failed to send recommendation: {pe}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

        logger.info(
            f"Created recommendation request with UID {uid} for {request.country} in {request.season}"
        )
        return {"uid": uid}

    except ValidationError as ve:
        logger.error(f"Validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as he:
        logger.error(f"HTTP error: {he}")
        raise
    except Exception as e:
        logger.error(f"Error creating recommendation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/recommendations/{uid}")
async def get_recommendation(uid: str):
    """
    Endpoint to retrieve a recommendation by UID.

    :param uid: Unique identifier for the recommendation.
    :return: JSON response with the recommendation data.
    """
    try:
        logger.info(f"Retrieving recommendation for UID {uid}")
        recommendation = await db_recommendations.find_one(
            {"uid": uid}, projection={"_id": False}
        )
        logger.info(f"Found {recommendation}")
    except Exception as e:
        logger.error(f"Error retrieving recommendation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        if not recommendation:
            logger.warning(f"Recommendation with UID {uid} not found")
            detail = {
                "error": "UID not found",
                "message": "The provided UID does not exist. Please check the UID and try again.",
            }
            raise HTTPException(status_code=404, detail=detail)
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


if __name__ == "__main__":
    # Run the FastAPI application with Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
