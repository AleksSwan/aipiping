from typing import List, Optional, Type, Union

from beanie import Document, View, init_beanie
from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import ValidationError
from pymongo.errors import OperationFailure, PyMongoError

from shared.errors.repository_errors import DatabaseConnectionError, RepositoryError
from shared.models.recommendations import RecommendationModel
from shared.repositories.abstract_repository import RecommendationBaseRepository
from shared.utils.logger_utils import LoggerConfigurator

logger = LoggerConfigurator(name="repository-recommendation").configure()


class MongoRepository(RecommendationBaseRepository):
    def __init__(
        self,
        db_uri: str = "mongodb://mongodb:27017",
        db_name: str = "travel_recommendations",
        document_models: Union[List[Type[Document] | Type[View] | str] | None] = [
            RecommendationModel
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

    async def find_one(self, filter_dict: dict) -> Optional[dict]:
        try:
            find_result = await RecommendationModel.find_one(filter_dict)
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
    ) -> Optional[RecommendationModel]:
        try:
            recommendation = await RecommendationModel.find_one(filter_dict)
            if recommendation:
                await recommendation.update(update_dict)
                return recommendation
        except OperationFailure as error:
            logger.error(f"Error while updating document: {error}")
        except PyMongoError as error:
            logger.error(f"Error while updating document: {error}")
        return None

    async def insert_one(self, document: dict) -> Optional[RecommendationModel]:
        try:
            recommendation = RecommendationModel(**document)
            await recommendation.insert()
            return recommendation
        except OperationFailure as e:
            logger.error(f"Connection error while inserting document: {e}")
            raise RepositoryError() from e
        except PyMongoError as e:
            logger.error(f"General PyMongoError while inserting document: {e}")
            raise RepositoryError() from e
        except Exception as e:
            logger.error(f"Unexpected error while inserting document: {e}")
            raise RepositoryError() from e
        return None

    async def disconnect(self):
        """Disconnects from the database."""
        if self.client is None:
            raise RepositoryError("Client not set")
        self.client.close()
        logger.info("Disconnected from the database")
