import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from aiokafka.errors import KafkaConnectionError

from worker import (
    consume,
    db_recommendations,
    generate_recommendations,
    process_recommendation,
)


@pytest.fixture
def mock_db_recommendations():
    """
    Mock repository.
    """
    mock_repo = AsyncMock(spec=db_recommendations)
    yield mock_repo


@pytest.fixture
def mock_kafka_consumer():
    """
    Mock Kafka consumer.
    """
    with patch("worker.AIOKafkaConsumer", autospec=True) as mock_consumer:
        yield mock_consumer


@pytest.fixture
def mock_groq_client():
    """
    Mock GROQ client.
    """
    with patch("worker.AsyncGroq", autospec=True) as mock_client:
        mock_instance = mock_client.return_value
        mock_chat = AsyncMock()
        mock_client.return_value.chat = mock_chat
        mock_create = AsyncMock()
        mock_chat.completions.create = mock_create
        yield mock_client


@pytest.mark.asyncio
async def test_generate_recommendations(mock_groq_client):
    """
    Test recommendation generation.
    """
    prompt = "Give three things to do in Canada during winter"
    expected_recommendations = {
        "1": "Skiing in the Rockies",
        "2": "Visit Niagara Falls",
        "3": "Explore Quebec City",
    }

    mock_groq_client().chat.completions.create.return_value.choices[
        0
    ].message.content = json.dumps(expected_recommendations)

    recommendations = await generate_recommendations(prompt)

    assert recommendations == expected_recommendations
    mock_groq_client().chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_process_recommendation(mock_db_recommendations, mock_groq_client):
    """
    Test recommendation processing.
    """
    uid = "1234"
    recommendation = {
        "uid": uid,
        "country": "Canada",
        "season": "winter",
        "timestamp": datetime.utcnow(),
        "status": "pending",
        "recommendations": [],
    }

    mock_db_recommendations.find_one.return_value = recommendation
    mock_groq_client().chat.completions.create.return_value.choices[
        0
    ].message.content = json.dumps(
        {
            "1": "Skiing in the Rockies",
            "2": "Visit Niagara Falls",
            "3": "Explore Quebec City",
        }
    )

    await process_recommendation(uid, mock_db_recommendations)

    mock_db_recommendations.find_one.assert_called_once_with({"uid": uid})
    mock_db_recommendations.update_one.assert_called_once()
    update_args = mock_db_recommendations.update_one.call_args[0]
    assert update_args[0] == {"uid": uid}
    assert update_args[1]["$set"]["status"] == "completed"
    assert len(update_args[1]["$set"]["recommendations"]) == 3


@pytest.mark.asyncio
async def test_consume(mock_db_recommendations, mock_kafka_consumer):
    """
    Test Kafka consumption.
    """
    mock_consumer_instance = mock_kafka_consumer.return_value
    mock_consumer_instance.start = AsyncMock()
    mock_consumer_instance.stop = AsyncMock()
    mock_consumer_instance.__aiter__.return_value = [AsyncMock(value=b"test_uid")]

    with patch("worker.process_recommendation") as mock_process_recommendation:
        mock_process_recommendation.return_value = AsyncMock()

        await consume(mock_db_recommendations)

        mock_process_recommendation.assert_awaited_once_with(
            "test_uid", mock_db_recommendations
        )

    mock_kafka_consumer.assert_called_once_with(
        "recommendations",
        bootstrap_servers="kafka:9092",
        group_id="recommendation_group",
    )
    mock_consumer_instance.start.assert_called_once()
    mock_consumer_instance.stop.assert_called_once()


@pytest.mark.asyncio
async def test_consume_kafka_error(mock_db_recommendations, mock_kafka_consumer):
    """
    Test Kafka connection error handling.
    """
    mock_consumer_instance = mock_kafka_consumer.return_value
    mock_consumer_instance.start = AsyncMock(
        side_effect=KafkaConnectionError("Failed to connect")
    )
    mock_consumer_instance.stop = AsyncMock()

    with pytest.raises(KafkaConnectionError):
        await consume(mock_db_recommendations)

    mock_consumer_instance.start.assert_called_once()
    mock_consumer_instance.stop.assert_called_once()
    mock_db_recommendations.update_one.assert_not_called()
