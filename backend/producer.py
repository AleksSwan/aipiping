import asyncio
from abc import ABC, abstractmethod

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaError

from errors import ProducerConnectionError, ProducerError
from logger_configurator import LoggerConfigurator

# Configure the logger
logger = LoggerConfigurator(name=__name__).configure()


class AbstractProducer(ABC):
    """
    Abstract base class for a message producer.
    This class defines the interface that any concrete implementation of
    a message producer must implement.
    """

    @abstractmethod
    async def start(self):
        """
        Abstract method to start the producer.
        """
        pass

    @abstractmethod
    async def stop(self):
        """
        Abstract method to stop the producer.
        """
        pass

    @abstractmethod
    async def send_and_wait(self, topic, message):
        """
        Abstract method to send a message to a specified topic and wait for the result.

        :param topic: The topic to which the message will be sent.
        :param message: The message to be sent.
        """
        pass


class KafkaProducer(AbstractProducer):
    """
    Concrete implementation of AbstractProducer using Kafka.
    This class interacts with Kafka to produce and send messages.
    """

    def __init__(self, bootstrap_servers):
        """
        Initialize the KafkaProducer with Kafka bootstrap servers.

        :param bootstrap_servers: A list of Kafka bootstrap servers.
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

    async def start(self):
        """
        Start the Kafka producer by initializing the AIOKafkaProducer.

        :raises ProducerConnectionError: If the connection to Kafka fails.
        """
        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        try:
            await self.producer.start()
        except KafkaConnectionError:
            logger.error("Failed to connect to Kafka")
            await self.stop()
            raise ProducerConnectionError("Failed to connect to Kafka")
        logger.info("Kafka producer started")

    async def stop(self):
        """
        Stop the Kafka producer if it is running.
        """
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def send_and_wait(self, topic, message):
        """
        Send a message to a specified Kafka topic and wait for the result.

        :param topic: The Kafka topic to which the message will be sent.
        :param message: The message to be sent, which will be encoded to UTF-8.
        :raises ProducerError: If the producer is not started or if message sending fails.
        """
        if not self.producer:
            raise ProducerError("Kafka producer is not started")
        try:
            await self.producer.send_and_wait(topic, message.encode("utf-8"))
        except KafkaError as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            raise ProducerError(f"Failed to send message to Kafka: {e}")
        else:
            logger.info(f"Message sent to Kafka topic [{topic}]: {message}")
