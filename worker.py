import logging
from aiokafka import AIOKafkaConsumer
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from asyncio import Semaphore
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('worker.log')

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Semaphore to limit concurrent requests
semaphore = Semaphore(5)  # Adjust the value as needed


async def consume():
    consumer = AIOKafkaConsumer(
        'recommendations',
        bootstrap_servers='kafka:9092',
        group_id='recommendation_group')
    await consumer.start()
    try:
        async for msg in consumer:
            uid = msg.value.decode('utf-8')
            await process_recommendation(uid)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")
    finally:
        await consumer.stop()


async def process_recommendation(uid: str):
    async with semaphore:  # Acquire semaphore before processing
        try:
            client = AsyncIOMotorClient('mongodb://mongodb:27017')
            db = client.travel_recommendations
            collection = db.recommendations
            recommendation = await collection.find_one({"uid": uid})
            if not recommendation:
                logger.error(f"Recommendation with UID {uid} not found in database.")
                return

            # Simulate OpenAI API call
            recommendations = [
                "Visit the Eiffel Tower.",
                "Explore the Louvre Museum.",
                "Walk along the Champs-Élysées."
            ]

            # Calculate processing time
            request_time = recommendation["timestamp"]
            processing_time = datetime.utcnow() - request_time

            # Update recommendation
            await collection.update_one(
                {"uid": uid},
                {"$set": {
                    "status": "completed",
                    "recommendations": recommendations,
                    "processing_time": processing_time.total_seconds()
                    }
                }
            )
            logger.info(f"Processed recommendation for UID {uid}")
        except Exception as e:
            logger.error(f"Error processing recommendation for UID {uid}: {e}")
            await collection.update_one(
                {"uid": uid},
                {"$set": {"status": "error", "recommendations": [], "error": str(e)}}
            )


async def main():
    limit_errors = 4
    error_count = 0
    while True and error_count < limit_errors:
        try:
            await consume()
        except Exception as e:
            error_count += 1
            logger.error(f"Fatal error in consumer loop: {e}")
            logger.info("Retrying consumer after a short delay...")


if __name__ == "__main__":
    asyncio.run(main())
