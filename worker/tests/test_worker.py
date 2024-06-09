import json
from asyncio import Semaphore
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiokafka.errors import KafkaConnectionError, KafkaError  # type: ignore
from app.consumers.kafka_consumer import consume
from app.main import AIOKafkaConsumer, db_recommendations, main
from app.services.groq_service import GroqService
from app.services.recommendation_service import RecommendationService

from shared.exceptions.custom_exeptions import DatabaseConnectionError


@pytest.fixture
def semaphore():
    """
    Fixture that provides a Semaphore object with an initial value of 3.
    """
    yield Semaphore(3)


@pytest.fixture
def mock_db_recommendations():
    """
    Fixture that creates a mock object of `db_recommendations`
    and sets its `initialize` method to return an `AsyncMock`.
    """
    mock_db = AsyncMock(spec=db_recommendations)
    mock_db.initialize.return_value = AsyncMock()
    yield mock_db


@pytest.fixture
def mock_main_consume():
    """
    Creates a mock object of the `consume` function using `AsyncMock` and returns it.
    """
    mock_consume = AsyncMock(spec=consume)
    yield mock_consume


@pytest.fixture
def mock_kafka_consumer():
    """
    Creates a mock object of the `AIOKafkaConsumer` class from the `app.main` module
    using the `patch` context manager.
    """
    with patch("app.main.AIOKafkaConsumer", autospec=True) as mock_consumer:
        yield mock_consumer


@pytest.fixture
def mock_groq_client():
    """
    Creates a mock Groq client.
    """
    with patch("app.services.groq_service.GroqService", autospec=True) as mock_client:
        mock_chat = AsyncMock()
        mock_client.chat = mock_chat
        mock_create = AsyncMock()
        mock_client.chat.completions.create = mock_create
        yield mock_client


@pytest.fixture
def mock_recommendation_service(mock_db_recommendations, mock_groq_client):
    """
    Creates a mock RecommendationService object with the provided mock_db_recommendations and mock_groq_client.

    Parameters:
        mock_db_recommendations (Mock): A mock object of the db_recommendations.
        mock_groq_client (Mock): A mock object of the groq_client.
    """
    moc_service = RecommendationService(
        db_recommendations=mock_db_recommendations,
        groq_service=mock_groq_client,
    )
    yield moc_service


@pytest.fixture
def groq_service():
    """
    Fixture returns an instance of the `GroqService` class.
    """
    return GroqService()


def test_system_message(groq_service):
    """
    Test the `_system_message` method of the `GroqService` class.
    """
    system_message = groq_service._system_message()
    assert system_message == {
        "role": "system",
        "content": (
            "You are a helpful tourist consultant. "
            "You must recommend three things to do in a given country during a specific season. "
            "Your answer must be short and concise. "
            "Don't use markdown in your answers. "
            "Return answer in JSON format with recommendation number as dictionary key."
        ),
    }


@pytest.mark.asyncio
async def test_generate_recommendations_valid(groq_service):
    """
    Test the `generate_recommendations` method of the `GroqService` class.
    """
    prompt = "Give three things to do in Canada during winter"
    expected_recommendations = {
        "1": "Skiing in the Rockies",
        "2": "Visit Niagara Falls",
        "3": "Explore Quebec City",
    }

    with patch.object(
        groq_service,
        "_chat_completion",
        return_value=json.dumps(expected_recommendations),
    ):
        recommendations = await groq_service.generate_recommendations(prompt)

        assert recommendations == expected_recommendations
        groq_service._chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_generate_recommendations_no_matching_items(groq_service):
    """
    Test the `generate_recommendations` method of the `GroqService` class.
    """
    prompt = "Give three things to do in Canada during winter"
    expected_recommendations = {"1": "No recommendations available"}

    with patch.object(groq_service, "_chat_completion", return_value=None):
        recommendations = await groq_service.generate_recommendations(prompt)

        assert recommendations == expected_recommendations
        groq_service._chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_generate_recommendations_not_json_format(groq_service):
    """
    Test the `generate_recommendations` method of the `GroqService` class when
    the response from `_chat_completion` is not in JSON format.
    """
    prompt = "Give three things to do in Canada during winter"
    message = "Not JSON format"
    expected_recommendations = {"1": message}

    with patch.object(groq_service, "_chat_completion", return_value=message):
        recommendations = await groq_service.generate_recommendations(prompt)

        assert recommendations == expected_recommendations
        groq_service._chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_process_recommendation(
    mock_db_recommendations, mock_groq_client, semaphore, mock_recommendation_service
):
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
    generated_recommendations = {
        "1": "Skiing in the Rockies",
        "2": "Visit Niagara Falls",
        "3": "Explore Quebec City",
    }

    mock_groq_client.generate_recommendations.return_value = generated_recommendations

    await mock_recommendation_service.process_recommendation(
        uid=uid,
        semaphore=semaphore,
    )

    mock_db_recommendations.find_one.assert_called_once_with(filter_dict={"uid": uid})
    mock_db_recommendations.update_one.assert_called_once()
    update_args = mock_db_recommendations.update_one.call_args[0]
    assert update_args[0] == {"uid": uid}
    assert update_args[1]["$set"]["status"] == "completed"
    assert len(update_args[1]["$set"]["recommendations"]) == 3


@pytest.mark.asyncio
async def test_consume(
    mock_db_recommendations,
    mock_kafka_consumer,
    mock_groq_client,
    semaphore,
    mock_recommendation_service,
):
    """
    Test the `consume` function.
    """
    mock_consumer_instance = mock_kafka_consumer
    mock_consumer_instance.start = AsyncMock()
    mock_consumer_instance._closed = False
    mock_consumer_instance.stop = AsyncMock()
    mock_consumer_instance.__aiter__.return_value = [AsyncMock(value=b"test_uid")]

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
    generated_recommendations = {
        "1": "Skiing in the Rockies",
        "2": "Visit Niagara Falls",
        "3": "Explore Quebec City",
    }

    mock_groq_client.generate_recommendations.return_value = generated_recommendations

    await consume(
        db_recommendations=mock_db_recommendations,
        consumer=mock_consumer_instance,
        groq_service=mock_groq_client,
        recommendation_service=mock_recommendation_service,
        semaphore=semaphore,
    )

    mock_groq_client.generate_recommendations.assert_called_once()
    mock_consumer_instance.start.assert_called_once()
    mock_consumer_instance.stop.assert_called_once()


@pytest.mark.asyncio
async def test_consume_kafka_error(
    mock_db_recommendations,
    mock_kafka_consumer,
    mock_groq_client,
    semaphore,
    mock_recommendation_service,
):
    """
    Test Kafka connection error handling.
    """
    mock_consumer_instance = mock_kafka_consumer.return_value
    mock_consumer_instance.start.side_effect = KafkaConnectionError("Failed to connect")

    mock_consumer_instance.stop = AsyncMock()

    with pytest.raises(KafkaConnectionError):
        await consume(
            db_recommendations=mock_db_recommendations,
            consumer=mock_consumer_instance,
            groq_service=mock_groq_client,
            recommendation_service=mock_recommendation_service,
            semaphore=semaphore,
        )

    mock_consumer_instance.start.assert_called_once()
    mock_consumer_instance.stop.assert_called_once()
    mock_db_recommendations.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_main_successful_consumption(
    mock_db_recommendations, mock_main_consume, mock_recommendation_service
):
    """
    Test the `main` function when it successfully consumes messages from Kafka.
    """
    db_recommendations = mock_db_recommendations
    groq_service = MagicMock(spec=GroqService)
    kafka_consumer = AsyncMock(spec=AIOKafkaConsumer)
    mock_consumer = MagicMock()
    mock_consumer.return_value = kafka_consumer
    mock_main_consume.return_value = None

    r = await main(
        db_recommendations=db_recommendations,
        kafka_consumer=mock_consumer,
        groq_service=groq_service,
        recommendator=mock_recommendation_service,
        limit_errors=0,
    )

    assert r == 0
    assert db_recommendations.initialize.called
    assert not mock_main_consume.called


@pytest.mark.asyncio
async def test_main_database_connection_error(
    mock_db_recommendations, mock_recommendation_service
):
    """
    Test the `main` function when the database connection fails.
    """
    db_recommendations = mock_db_recommendations
    db_recommendations.initialize.side_effect = DatabaseConnectionError("Test error")
    groq_service = MagicMock(spec=GroqService)
    kafka_consumer = AsyncMock(spec=AIOKafkaConsumer)
    kafka_consumer._closed = False

    await main(
        db_recommendations=db_recommendations,
        kafka_consumer=kafka_consumer,
        groq_service=groq_service,
        recommendator=mock_recommendation_service,
    )

    assert db_recommendations.initialize.called
    assert not kafka_consumer.start.called
    assert not kafka_consumer.stop.called
    assert not kafka_consumer.return_value.__aenter__.called
    assert not kafka_consumer.return_value.__aexit__.called


@pytest.mark.asyncio
async def test_main_kafka_connection_error(
    mock_db_recommendations, mock_recommendation_service
):
    """
    Test the `main` function when there is a Kafka connection error.
    """
    db_recommendations = mock_db_recommendations
    groq_service = MagicMock(spec=GroqService)
    kafka_consumer = AsyncMock(spec=AIOKafkaConsumer)
    mock_consumer = MagicMock()
    mock_consumer.return_value = kafka_consumer
    kafka_consumer.start.side_effect = KafkaConnectionError("Test error")

    limit_errors = 2
    await main(
        db_recommendations=db_recommendations,
        kafka_consumer=mock_consumer,
        groq_service=groq_service,
        recommendator=mock_recommendation_service,
        limit_errors=limit_errors,
    )

    assert db_recommendations.initialize.called
    assert kafka_consumer.start.called
    assert kafka_consumer.stop.called
    assert kafka_consumer.start.await_count == limit_errors
    assert kafka_consumer.stop.await_count == limit_errors
    assert not kafka_consumer.return_value.__aenter__.called
    assert not kafka_consumer.return_value.__aexit__.called


@pytest.mark.asyncio
async def test_main_kafka_consumption_error(
    mock_db_recommendations, semaphore, mock_recommendation_service
):
    """
    Test the `main` function when there is a Kafka consumption error.
    """
    db_recommendations = mock_db_recommendations
    groq_service = MagicMock(spec=GroqService)
    kafka_consumer = AsyncMock(spec=AIOKafkaConsumer)
    kafka_consumer.start.side_effect = KafkaError("Test error")

    with pytest.raises(KafkaError):
        await consume(
            db_recommendations=db_recommendations,
            consumer=kafka_consumer,
            groq_service=groq_service,
            recommendation_service=mock_recommendation_service,
            semaphore=semaphore,
        )

    assert kafka_consumer.start.called
    assert kafka_consumer.stop.called
    assert kafka_consumer.start.await_count == 1
    assert kafka_consumer.stop.await_count == 1
    assert not kafka_consumer.return_value.__aenter__.called
    assert not kafka_consumer.return_value.__aexit__.called
