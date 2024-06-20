from abc import ABC, abstractmethod
from typing import Coroutine, Union


class AbstractProducer(ABC):
    """
    Abstract base class for a message producer.
    This class defines the interface that any concrete implementation of
    a message producer must implement.
    """

    @abstractmethod
    async def start(self) -> Union[Coroutine, Exception, None]:
        """Abstract method to start the producer."""
        raise NotImplementedError(
            "The start method must be implemented by subclasses of AbstractProducer"
        )

    @abstractmethod
    async def stop(self) -> Union[Coroutine, Exception, None]:
        """Abstract method to stop the producer."""
        raise NotImplementedError(
            "The stop method must be implemented by subclasses of AbstractProducer"
        )

    @abstractmethod
    async def send_and_wait(self, topic, message) -> Union[Coroutine, Exception, None]:
        """Abstract method to send a message to a specified topic and wait for the result."""
        raise NotImplementedError(
            "The send_and_wait method must be implemented by subclasses of AbstractProducer"
        )
