import uuid
from typing import Optional
from unittest.mock import AsyncMock, patch

import pytest
from app_backend.main import app
from app_backend.routes.recommendations import create_recommendation
from app_backend.services.recommendation_service import RecommendationService
from fastapi import status
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from shared.errors.backend_errors import CreateRecommendationError
from shared.errors.producer_errors import ProducerError
from shared.errors.repository_errors import RepositoryError
from shared.models.recommendations_requests import RecommendationRequest


@pytest.fixture
def test_request():
    """Fixture that returns a RecommendationRequest object for testing purposes"""
    return RecommendationRequest(country="Canada", season="winter")


@pytest.fixture
def client():
    """Fixture to create a TestClient for the FastAPI app."""

    return TestClient(app)


@pytest.fixture
def mock_producer():
    """Fixture to mock the producer."""
    with patch(
        "app_backend.main.get_producer", new_callable=AsyncMock
    ) as mock_producer:
        yield mock_producer


@pytest.fixture
def mock_db():
    """Fixture to mock the repository."""
    with patch("app_backend.main.get_db", new_callable=AsyncMock) as mock_db:
        yield mock_db


@pytest.fixture
def mock_recommendation_service(mock_db, mock_producer):
    """
    Fixture to mock the recommendation service.
    Parameters:
        mock_db: A mock database.
        mock_producer: A mock producer.
    """
    mock_service = RecommendationService()
    mock_service.repository = mock_db
    mock_service.producer = mock_producer
    yield mock_service


@pytest.fixture
def service_for_mock():
    return RecommendationService()


@pytest.mark.asyncio
async def test_create_recommendation(client):
    """
    Test case for creating a recommendation.
    """
    with patch.object(
        RecommendationService, "create_recommendation", return_value=uuid.uuid4()
    ):
        response = client.post(
            "/recommendations", json={"country": "Canada", "season": "winter"}
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        # Check response expected field
        assert "uid" in data
        # Check response UID format
        uid_split = data["uid"].split("-")
        assert len(uid_split) == 5
        # Check response UID version
        assert uid_split[2][0] == "4"


@pytest.mark.asyncio
async def test_create_recommendation_invalid_country(client):
    """
    Test case for creating a recommendation with an invalid country.
    """
    response = client.post(
        "/recommendations", json={"country": "InvalidCountry", "season": "winter"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"] == "Country 'InvalidCountry' is not found."

    response = client.post(
        "/recommendations", json={"country": "eng", "season": "winter"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Similar countries found" in data["detail"]


@pytest.mark.asyncio
async def test_create_recommendation_invalid_season(client):
    """
    Test case for creating a recommendation with an invalid season.
    """
    response = client.post(
        "/recommendations", json={"country": "Canada", "season": "invalidSeason"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"] == "Season 'invalidSeason' is not supported."


@pytest.mark.asyncio
async def test_get_recommendation(client, mock_recommendation_service):
    """
    Test case for retrieving a recommendation.
    """
    uid = "test-uid"
    return_value = {
        "uid": uid,
        "country": "Canada",
        "season": "winter",
        "status": "completed",
        "recommendations": ["Skiing", "Ice skating", "Hot springs"],
    }
    mock_recommendation_service.repository.find_one.return_value = return_value

    response = client.get(f"/recommendations/{uid}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(key in data for key in return_value.keys())
    assert data["uid"] == uid
    assert data["status"] == "completed"
    assert data["recommendations"] == ["Skiing", "Ice skating", "Hot springs"]


@pytest.mark.asyncio
async def test_get_recommendation_not_found(client, mock_recommendation_service):
    """
    Test case for retrieving a recommendation that does not exist.
    """
    uid = "non-existent-uid"
    mock_recommendation_service.repository.find_one.return_value = None

    response = client.get(f"/recommendations/{uid}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["detail"]["error"] == "UID not found"


@pytest.mark.parametrize("data_status", ["pending", "error"])
@pytest.mark.asyncio
async def test_get_recommendation_unprocessable_by_status(
    client, mock_recommendation_service, data_status
):
    """
    Test case for retrieving a recommendation that does not exist.
    """
    uid = "non-existent-uid"
    return_value = {
        "uid": uid,
        "country": "Canada",
        "season": "winter",
        "status": data_status,
        "recommendations": ["Skiing", "Ice skating", "Hot springs"],
    }
    mock_recommendation_service.repository.find_one.return_value = return_value
    response = client.get(f"/recommendations/{uid}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert data["detail"]["error"] == "Task not completed"


@pytest.mark.asyncio
async def test_get_recommendation_status_pending(
    client, mock_db, mock_recommendation_service
):
    """
    Test case for retrieving a pending recommendation.
    """
    uid = "pending-uid"
    mock_recommendation_service.repository.find_one.return_value = {
        "uid": uid,
        "status": "pending",
    }

    response = client.get(f"/recommendations/{uid}/status")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "pending"
    assert "message" in data
    assert "recommendations" not in data


@pytest.mark.asyncio
async def test_get_recommendation_status_error(
    client, mock_db, mock_recommendation_service
):
    """
    Test case for retrieving a recommendation that encountered an error.
    """
    uid = "error-uid"
    mock_recommendation_service.repository.find_one.return_value = {
        "uid": uid,
        "status": "error",
    }

    response = client.get(f"/recommendations/{uid}/status")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "error"
    assert "message" in data


def test_create_recommendation_success(
    client, test_request, mock_recommendation_service
):
    response = client.post("/recommendations", json=test_request.model_dump())
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "uid" in response.json()


def test_create_recommendation_validation_error(
    client, mock_recommendation_service, test_request
):
    mock_recommendation_service.create_recommendation = AsyncMock()
    validation_error = ValidationError.from_exception_data(
        "Invalid data", line_errors=[]
    )

    mock_recommendation_service.create_recommendation.side_effect = validation_error
    response = client.post("/recommendations", json=test_request.model_dump())
    assert response.status_code == 400


@pytest.mark.parametrize("tested_exeption", [ProducerError, RepositoryError, Exception])
def test_create_recommendation_errors_with_response_status_code_500(
    client, mock_recommendation_service, tested_exeption, test_request
):
    # Mock the recommendation service to raise a exeptions
    mock_recommendation_service.create_recommendation = AsyncMock()
    mock_recommendation_service.create_recommendation.side_effect = tested_exeption

    response = client.post("/recommendations", json=test_request.model_dump())
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.parametrize("tested_exeption", [CreateRecommendationError])
@pytest.mark.asyncio
async def test_create_recommendation_errors_with_response_status_code_400(
    client, mock_recommendation_service, tested_exeption, test_request
):
    # Mock the recommendation service to raise a exeptions
    mock_recommendation_service.create_recommendation = AsyncMock()
    mock_recommendation_service.create_recommendation.side_effect = tested_exeption(
        ["Error"]
    )
    response = client.post("/recommendations", json=test_request.model_dump())

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_create_recommendation_successful(
    mock_recommendation_service, test_request, client
):
    uid = str(uuid.uuid4())
    mock_recommendation_service.create_recommendation = AsyncMock(return_value=uid)

    result: Optional[dict] = await create_recommendation(
        test_request, mock_recommendation_service
    )
    assert "uid" in result.keys() if result else []
    # check UUID v4 forma
    assert "-" in result["uid"] if result else []
    result_uid_split = result["uid"].split("-") if result else []
    assert len(result_uid_split) == 5
    assert result_uid_split[2][0] == "4"

    with patch.object(RecommendationService, "create_recommendation", return_value=uid):
        response = client.post("/recommendations", json=test_request.model_dump())
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"uid": uid}


@pytest.mark.asyncio
async def test_read_hello(test_request, mock_recommendation_service):
    return_value = str(uuid.uuid4())
    with patch.object(
        mock_recommendation_service, "create_recommendation", return_value=return_value
    ):
        transport = ASGITransport(app)  # type: ignore
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/recommendations", json=test_request.model_dump())
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"uid": return_value}
