from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import SUPPORTED_SEASONS, app
from producer import AbstractProducer
from repository import AbstractRecommendationRepository


@pytest.fixture
def client():
    """
    Fixture to create a TestClient for the FastAPI app.
    """
    return TestClient(app)


@pytest.fixture
def mock_producer():
    """
    Fixture to mock the producer.
    """
    with patch("main.producer", new_callable=AsyncMock) as mock_producer:
        yield mock_producer


@pytest.fixture
def mock_db():
    """
    Fixture to mock the repository.
    """
    with patch("main.db_recommendations", new_callable=AsyncMock) as mock_db:
        yield mock_db


@pytest.mark.asyncio
async def test_create_recommendation(client, mock_producer, mock_db):
    """
    Test case for creating a recommendation.
    """
    response = client.post(
        "/recommendations", json={"country": "Canada", "season": "winter"}
    )
    assert response.status_code == 202
    data = response.json()
    assert "uid" in data


@pytest.mark.asyncio
async def test_create_recommendation_invalid_country(client):
    """
    Test case for creating a recommendation with an invalid country.
    """
    response = client.post(
        "/recommendations", json={"country": "InvalidCountry", "season": "winter"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Country 'InvalidCountry' is not found."


@pytest.mark.asyncio
async def test_create_recommendation_invalid_season(client):
    """
    Test case for creating a recommendation with an invalid season.
    """
    response = client.post(
        "/recommendations", json={"country": "Canada", "season": "invalidSeason"}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Season 'invalidSeason' is not supported."


@pytest.mark.asyncio
async def test_get_recommendation(client, mock_db):
    """
    Test case for retrieving a recommendation.
    """
    uid = "test-uid"
    mock_db.find_one.return_value = {
        "uid": uid,
        "country": "Canada",
        "season": "winter",
        "status": "completed",
        "recommendations": ["Skiing", "Ice skating", "Hot springs"],
    }

    response = client.get(f"/recommendations/{uid}")
    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == uid
    assert data["status"] == "completed"
    assert data["recommendations"] == ["Skiing", "Ice skating", "Hot springs"]


@pytest.mark.asyncio
async def test_get_recommendation_not_found(client, mock_db):
    """
    Test case for retrieving a recommendation that does not exist.
    """
    uid = "non-existent-uid"
    mock_db.find_one.return_value = None

    response = client.get(f"/recommendations/{uid}")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"] == "UID not found"


@pytest.mark.asyncio
async def test_get_recommendation_pending(client, mock_db):
    """
    Test case for retrieving a pending recommendation.
    """
    uid = "pending-uid"
    mock_db.find_one.return_value = {
        "uid": uid,
        "status": "pending",
    }

    response = client.get(f"/recommendations/{uid}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert "message" in data


@pytest.mark.asyncio
async def test_get_recommendation_error(client, mock_db):
    """
    Test case for retrieving a recommendation that encountered an error.
    """
    uid = "error-uid"
    mock_db.find_one.return_value = {
        "uid": uid,
        "status": "error",
    }

    response = client.get(f"/recommendations/{uid}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "message" in data
