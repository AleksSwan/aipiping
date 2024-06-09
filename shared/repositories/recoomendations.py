from abc import ABC, abstractmethod
from typing import List, Optional, Type, Union

from beanie import Document, View, init_beanie
from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import ValidationError
from pymongo.errors import OperationFailure, PyMongoError

from shared.exceptions.custom_exeptions import DatabaseConnectionError
from shared.models.recommendations import Recommendation
from shared.utils.logger_configurator import LoggerConfigurator

logger = LoggerConfigurator(name=__name__).configure()


class RecommendationBaseRepository(ABC):
    """
    Abstract base class for a recommendation repository.
    This class defines the interface that any concrete implementation of
    a recommendation repository must implement.
    """

    @abstractmethod
    async def initialize(self):
        raise NotImplementedError(
            "The initialize method must be implemented by subclasses of RecommendationRepository."
        )

    @abstractmethod
    async def find_one(self, filter_dict: dict, *args, **kwargs):
        """
        Abstract method to find a single document based on a filter.

        :param filter: A dictionary specifying the filter criteria.
        """
        raise NotImplementedError(
            "The find_one method must be implemented by subclasses of RecommendationRepository."
        )

    @abstractmethod
    async def update_one(self, filter_dict: dict, new_values_dict: dict):
        """
        Abstract method to update a single document based on a filter.

        :param filter: A dictionary specifying the filter criteria.
        :param new_values: A dictionary specifying the new values to update.
        """
        raise NotImplementedError(
            "The update_one method must be implemented by subclasses of RecommendationRepository."
        )

    @abstractmethod
    async def insert_one(self, document: dict):
        """
        Abstract method to insert a single document into the collection.

        :param document: A dictionary representing the document to insert.
        :return: The result of the insert operation.
        """
        raise NotImplementedError(
            "The insert_one method must be implemented by subclasses of RecommendationRepository."
        )


class MongoRepository(RecommendationBaseRepository):
    def __init__(
        self,
        db_uri: str = "mongodb://mongodb:27017",
        db_name: str = "travel_recommendations",
        document_models: Union[List[Type[Document] | Type[View] | str] | None] = [
            Recommendation
        ],
    ):
        self.client: AgnosticClient = AsyncIOMotorClient(db_uri)
        self.db = self.client[db_name]
        self.document_models = document_models

    async def initialize(self):
        try:
            await init_beanie(database=self.db, document_models=self.document_models)
        except Exception as error:
            logger.error(f"Failed to initialize the beanie database: {error}")
            raise DatabaseConnectionError(
                "Failed to initialize the beanie database"
            ) from error
        logger.info("Initialized the beanie database")

    async def find_one(self, filter_dict: dict, *args, **kwargs) -> Optional[dict]:
        try:
            find_result = await Recommendation.find_one(filter_dict, *args, **kwargs)
            return dict(find_result) if find_result else None
        except ValidationError as e:
            logger.error(f"Validation Error: {e}")
            for error in e.errors():
                logger.error(f"Field: {error['loc'][0]}, Error: {error['msg']}")
        except OperationFailure as error:
            logger.error(f"Error while finding document: {error}")
        except PyMongoError as error:
            logger.error(f"Error while finding document: {error}")
        except Exception as error:
            logger.error(f"Unexpected error while finding document: {error}")
        return None

    async def update_one(
        self, filter_dict: dict, update_dict: dict
    ) -> Optional[Recommendation]:
        try:
            recommendation = await Recommendation.find_one(filter_dict)
            if recommendation:
                await recommendation.update(update_dict)
                return recommendation
        except OperationFailure as error:
            logger.error(f"Error while updating document: {error}")
        except PyMongoError as error:
            logger.error(f"Error while updating document: {error}")
        return None

    async def insert_one(self, document: dict) -> Optional[Recommendation]:
        try:
            recommendation = Recommendation(**document)
            await recommendation.insert()
            return recommendation
        except OperationFailure as e:
            logger.error(f"Connection error while inserting document: {e}")
        except PyMongoError as e:
            logger.error(f"General PyMongoError while inserting document: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while inserting document: {e}")
        return None
