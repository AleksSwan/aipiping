import uuid
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError
from motor.motor_asyncio import AsyncIOMotorClient
from aiokafka import AIOKafkaProducer
from datetime import datetime, timedelta
import uvicorn

app = FastAPI()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('api.log')

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# MongoDB setup
client = AsyncIOMotorClient('mongodb://0.0.0.0:27017')
db = client.travel_recommendations
collection = db.recommendations

# Kafka setup
producer = None

# Supported countries, seasons, and times
SUPPORTED_COUNTRIES = {"Canada", "France", "Germany"}  # Add more countries as needed
SUPPORTED_SEASONS = {"winter", "spring", "summer", "fall"}

class RecommendationRequest(BaseModel):
    country: str = Field(..., example="Canada")
    season: str = Field(..., example="winter")


class Lifespan:
    def __init__(self, app: FastAPI):
        self.app = app

    async def __aenter__(self):
        global producer
        producer = AIOKafkaProducer(bootstrap_servers='0.0.0.0:9092')
        await producer.start()
        logger.info("Kafka producer started")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        global producer
        await producer.stop()
        logger.info("Kafka producer stopped")

app.router.lifespan_context = Lifespan

@app.get("/recommendations")
async def create_recommendation():
    return {"uid": f"{uuid.uuid4()}"}

@app.post("/recommendations", status_code=202)
async def create_recommendation(request: RecommendationRequest):
    try:
        if request.country not in SUPPORTED_COUNTRIES:
            raise HTTPException(status_code=400, detail=f"Country '{request.country}' is not supported.")
        if request.season not in SUPPORTED_SEASONS:
            raise HTTPException(status_code=400, detail=f"Season '{request.season}' is not supported.")

        uid = str(uuid.uuid4())
        logger.info(f"Generating UID {uid} for {request.country} in {request.season}")
        recommendation_data = {
            "uid": uid,
            "country": request.country,
            "season": request.season,
            "timestamp": datetime.utcnow(),
            "status": "pending",
            "recommendations": []
        }
        await collection.insert_one(recommendation_data)
        await producer.send_and_wait("recommendations", uid.encode('utf-8'))
        logger.info(f"Created recommendation request with UID {uid} for {request.country} in {request.season}")
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
    try:
        logger.info(f'Retrieving recommendation for UID {uid}')
        recommendation = await collection.find_one({"uid": uid})
    except Exception as e:
        logger.error(f"Error retrieving recommendation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        if not recommendation:
            logger.warning(f"Recommendation with UID {uid} not found")
            raise HTTPException(status_code=404, detail="UID not found")
        if recommendation["status"] == "pending":
            logger.info(f"Recommendation with UID {uid} is still pending")
            return {"uid": uid, "status": "pending", "message": "The recommendations are not yet available. Please try again later."}
        if recommendation["status"] == "error":
            logger.error(f"Error occurred while processing recommendation with UID {uid}")
            return {"uid": uid, "status": "error", "message": "An error occurred while processing your request. Please try again later."}
        
    logger.info(f"Retrieved recommendation for UID {uid}")
    return recommendation


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
