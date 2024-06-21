from typing import Annotated, Optional

from app_backend.dependencies import get_recommendation_service
from app_backend.services.recommendation_service import RecommendationService
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from shared.errors.backend_errors import (
    CreateRecommendationError,
    TaskNotCompletedError,
    UIDNotFoundError,
)
from shared.errors.producer_errors import ProducerError
from shared.errors.repository_errors import RepositoryError
from shared.models.recommendations import (
    RecommendationResponseModel,
    RecommendationStatusResponseModel,
)
from shared.models.recommendations_requests import RecommendationRequest
from shared.utils.logger_utils import LoggerConfigurator

logger = LoggerConfigurator(name="recommendation-routes").configure()

router: APIRouter = APIRouter(tags=["recommendations"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_recommendation(
    request: RecommendationRequest,
    recommendation_service: Annotated[
        RecommendationService, Depends(get_recommendation_service)
    ],
) -> Optional[dict]:
    """Creates a recommendation based on the provided `RecommendationRequest` object."""
    logger.debug(f"Request: {request}, {recommendation_service}")
    try:
        uid = await recommendation_service.create_recommendation(request)
        return {"uid": uid}
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ProducerError as e:
        logger.error(f"Producer error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
    except RepositoryError as e:
        logger.error(f"RepositoryError error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
    except CreateRecommendationError as e:
        logger.error(f"Error creating recommendation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Error creating recommendation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get("/{uid}")
async def get_recommendation(
    uid: str,
    recommendation_service: Annotated[
        RecommendationService, Depends(get_recommendation_service)
    ],
    response_model=RecommendationResponseModel,
) -> dict:
    """
    Endpoint to retrieve a recommendation by UID.

    :param uid: Unique identifier for the recommendation.
    :return: JSON response with the recommendation data.
    """
    try:
        recommendation = await recommendation_service.get_recommendation(uid)
        logger.debug(f"Got recommendation [{type(recommendation)}]: {recommendation}")
        response: dict = RecommendationResponseModel(**recommendation).model_dump(
            exclude_none=True, exclude_unset=True, exclude_defaults=True
        )
        logger.debug(f"Response: {response}")
        return response
    except RepositoryError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
    except UIDNotFoundError:
        detail = {
            "error": "UID not found",
            "message": "The provided UID does not exist. Please check the UID and try again.",
        }
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    except TaskNotCompletedError:
        detail = {
            "error": "Task not completed",
            "message": "Recommendation info for provided UID not fetched yet.",
        }
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )
    except Exception as e:
        logger.error(f"Error getting recommendation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get("/{uid}/status")
async def get_recommendation_status(
    uid: str,
    recommendation_service: Annotated[
        RecommendationService, Depends(get_recommendation_service)
    ],
    response_model=RecommendationStatusResponseModel,
) -> dict:
    """
    Endpoint to retrieve a recommendation by UID.

    :param uid: Unique identifier for the recommendation.
    :return: JSON response with the recommendation data.
    """
    try:
        recommendation_status = await recommendation_service.get_recommendation_status(
            uid
        )
        logger.debug(
            f"Got recommendation [{type(recommendation_status)}]: {recommendation_status}"
        )
        response: dict = RecommendationStatusResponseModel(
            **recommendation_status
        ).model_dump()
        logger.debug(f"Response: {response}")
        return response
    except RepositoryError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
    except UIDNotFoundError:
        detail = {
            "error": "UID not found",
            "message": "The provided UID does not exist. Please check the UID and try again.",
        }
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    except Exception as e:
        logger.error(f"Error getting recommendation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
