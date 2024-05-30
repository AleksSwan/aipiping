import asyncio
import json
import os
from asyncio import Semaphore
from datetime import datetime

import groq
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError, KafkaError
from groq import AsyncGroq

from logger_configurator import LoggerConfigurator
from repository import RecommendationRepository, MongoRepository

# Configure the logger
logger = LoggerConfigurator(name=__name__, log_file="worker.log").configure()

# Semaphore to limit concurrent requests
semaphore = Semaphore(5)  # Adjust the value as needed

# MongoDB repository for recommendations
db_recommendations = MongoRepository(
    uri="mongodb://mongodb:27017",
    db_name="travel_recommendations",
    collection_name="recommendations",
)


def groq_system_message():
    """
    Generate the system message for the Groq API request.
    This message provides the instructions for the AI assistant.

    :return: A list containing the system message.
    """
    return [
        {
            "role": "system",
            "content": (
                "You are a helpful tourist consultant. "
                "You must recommend three things to do in a given country during a specific season. "
                "Your answer must be short and concise. "
                "Don't use markdown in your answers. "
                "Return answer in JSON format with recommendation number as dictionary key."
            ),
        },
    ]


async def generate_recommendations(prompt: str) -> dict:
    """
    Generate travel recommendations using the Groq API based on the given prompt.

    :param prompt: The prompt to send to the Groq API.
    :return: A dictionary containing the recommendations.
    """
    client = AsyncGroq()
    messages = groq_system_message() + [{"role": "user", "content": prompt}]
    chat_completion = await client.chat.completions.create(
        messages=messages,
        model="llama3-70b-8192",
        temperature=0.01,
        max_tokens=1024,
        stop=None,
        stream=False,
    )
    recoomendations = chat_completion.choices[0].message.content
    try:
        recoomendations = json.loads(recoomendations)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse recommendations: {recoomendations}")
        recoomendations = {"1": recoomendations}
    logger.info(f"Recommendations for {prompt}: {recoomendations}")
    return recoomendations


async def consume(db_recommendations: RecommendationRepository):
    """
    Consume messages from the Kafka topic and process recommendations.

    :param db_recommendations: The repository to interact with the recommendations database.
    """
    consumer = AIOKafkaConsumer(
        "recommendations",
        bootstrap_servers="kafka:9092",
        group_id="recommendation_group",
    )
    try:
        await consumer.start()
        async for msg in consumer:
            uid = msg.value.decode("utf-8")
            await process_recommendation(uid, db_recommendations)
    finally:
        await consumer.stop()


async def process_recommendation(
    uid: str, db_recommendations: RecommendationRepository
):
    """
    Process a single recommendation request by generating recommendations and updating the database.

    :param uid: The unique identifier for the recommendation request.
    :param db_recommendations: The repository to interact with the recommendations database.
    """
    async with semaphore:  # Acquire semaphore before processing
        try:
            recommendation = await db_recommendations.find_one({"uid": uid})
            if not recommendation:
                logger.error(f"Recommendation with UID {uid} not found in database.")
                return

            # Generate recommendations
            country = recommendation.get("country")
            season = recommendation.get("season")
            prompt = f"Give three things to do in {country} during {season}"
            recommendations = await generate_recommendations(prompt)

            # Calculate processing time
            request_time = recommendation["timestamp"]
            processing_time = datetime.utcnow() - request_time

            # Update recommendation in the database
            await db_recommendations.update_one(
                {"uid": uid},
                {
                    "$set": {
                        "status": "completed",
                        "recommendations": list(recommendations.values()),
                        "processing_time": processing_time.total_seconds(),
                    }
                },
            )
            logger.info(f"Processed recommendation for UID {uid}")
        except Exception as e:
            logger.error(f"Error processing recommendation for UID {uid}: {e}")
            try:
                await db_recommendations.update_one(
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


async def main():
    """
    Main function to start the Kafka consumer and handle errors.
    """
    limit_errors = 5  # Number of errors before exiting
    error_count = 0
    logger.info(f"Starting worker with limit_errors = {limit_errors}")

    while True and error_count < limit_errors:
        try:
            await consume(db_recommendations)
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


if __name__ == "__main__":
    asyncio.run(main())
