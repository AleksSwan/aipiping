from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorClient

from logger_configurator import LoggerConfigurator

# Configure the logger
logger = LoggerConfigurator(name=__name__).configure()


class AbstractRecommendationRepository(ABC):
    @abstractmethod
    async def find_one(filter: dict):
        pass

    @abstractmethod
    async def update_one(filter: dict, new_values: dict):
        pass


class MongoRepository(AbstractRecommendationRepository):
    def __init__(
        self,
        uri: str,
        db_name: str = "travel_recommendations",
        collection_name: str = "recommendations",
    ):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def find_one(self, filter: dict, projection: dict = None):
        return self.collection.find_one(filter=filter, projection=projection)

    def update_one(self, filter: dict, update: dict):
        return self.collection.update_one(filter=filter, update=update)

    def insert_one(self, document: dict):
        return self.collection.insert_one(document=document)
