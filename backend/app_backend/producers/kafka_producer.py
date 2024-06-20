from typing import Coroutine, List, Union

from aiokafka import AIOKafkaProducer  # type: ignore
from aiokafka.errors import KafkaError  # type: ignore
from app_backend.producers.abstract_producer import AbstractProducer

from shared.errors.producer_errors import (
    ProducerError,
    ProducerStartError,
    ProducerStopError,
)
from shared.utils.logger_utils import LoggerConfigurator

# Configure the logger
logger = LoggerConfigurator(name="kafka-producer").configure()


class KafkaProducer(AbstractProducer):
    """
    Concrete implementation of AbstractProducer using Kafka.
    This class interacts with Kafka to produce and send messages.
    """

    def __init__(self, bootstrap_servers: Union[str, List[str]]):
        """
        Initialize the KafkaProducer with Kafka bootstrap servers.

        :param bootstrap_servers: A list of Kafka bootstrap servers.
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)

    async def start(self) -> Union[Coroutine, Exception, None]:
        """
        Start the Kafka producer.

        :raises ProducerStartError: If the starting Kafka producer fails.
        """
        try:
            await self.producer.start()
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise ProducerStartError("Failed to start Kafka producer") from e
        logger.info("Kafka producer started")
        return None

    async def stop(self) -> Union[Coroutine, Exception, None]:
        """
        Stop the Kafka producer if it is running.

        :raises ProducerStartError: If the stopping Kafka producer fails.
        """
        try:
            await self.producer.stop()
        except Exception as e:
            logger.error(f"Failed to stop Kafka producer: {e}")
            raise ProducerStopError("Failed to stop Kafka producer") from e
        logger.info("Kafka producer stopped")
        return None

    async def send_and_wait(
        self, topic: str, message: str
    ) -> Union[Coroutine, Exception, None]:
        """
        Send a message to a specified Kafka topic and wait for the result.

        :param topic: The Kafka topic to which the message will be sent.
        :param message: The message to be sent, which will be encoded to UTF-8.
        :raises ProducerError: If the producer is not started or if message sending fails.
        """
        try:
            await self.producer.send_and_wait(topic, message.encode("utf-8"))
        except KafkaError as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            raise ProducerError("Failed to send message to Kafka") from e
        else:
            logger.info(f"Message sent to Kafka topic [{topic}]: {message}")
        return None
