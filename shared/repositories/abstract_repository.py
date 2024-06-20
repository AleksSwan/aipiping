from abc import ABC, abstractmethod


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

    @abstractmethod
    async def disconnect(self):
        """Abstract method to disconnect from the database."""
        raise NotImplementedError(
            "The disconnect method must be implemented by subclasses of RecommendationRepository."
        )
