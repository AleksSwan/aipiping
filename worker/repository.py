from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorClient

from logger_configurator import LoggerConfigurator

# Configure the logger
logger = LoggerConfigurator(name=__name__).configure()


class RecommendationRepository(ABC):
    """
    Abstract base class for a recommendation repository.
    This class defines the interface that any concrete implementation of
    a recommendation repository must implement.
    """

    @abstractmethod
    async def find_one(self, filter: dict):
        """
        Abstract method to find a single document based on a filter.

        :param filter: A dictionary specifying the filter criteria.
        """
        raise NotImplementedError(
            "The find_one method must be implemented by subclasses of RecommendationRepository."
        )

    @abstractmethod
    async def update_one(self, filter: dict, new_values: dict):
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


class MongoRepository(RecommendationRepository):
    """
    Concrete implementation of AbstractRecommendationRepository using MongoDB.
    This class interacts with a MongoDB collection to perform CRUD operations.
    """

    def __init__(
        self,
        uri: str,
        db_name: str = "travel_recommendations",
        collection_name: str = "recommendations",
    ):
        """
        Initialize the MongoRepository with MongoDB connection details.

        :param uri: The MongoDB connection URI.
        :param db_name: The name of the database.
        :param collection_name: The name of the collection.
        """
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    async def find_one(self, filter: dict, projection: dict = None):
        """
        Find a single document in the collection based on a filter.

        :param filter: A dictionary specifying the filter criteria.
        :param projection: A dictionary specifying the fields to include or exclude.
        :return: The document that matches the filter criteria.
        """
        return await self.collection.find_one(filter=filter, projection=projection)

    async def update_one(self, filter: dict, update: dict):
        """
        Update a single document in the collection based on a filter.

        :param filter: A dictionary specifying the filter criteria.
        :param update: A dictionary specifying the update operations.
        :return: The result of the update operation.
        """
        return await self.collection.update_one(filter=filter, update=update)

    async def insert_one(self, document: dict):
        """
        Insert a single document into the collection.

        :param document: A dictionary representing the document to insert.
        :return: The result of the insert operation.
        """
        return await self.collection.insert_one(document=document)
