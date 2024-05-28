import asyncio
from abc import ABC, abstractmethod

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaError

from errors import ProducerConnectionError, ProducerError
from logger_configurator import LoggerConfigurator

# Configure the logger
logger = LoggerConfigurator(name=__name__).configure()


class AbstractProducer(ABC):
    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def send_and_wait(self, topic, message):
        pass


class KafkaProducer(AbstractProducer):
    def __init__(self, bootstrap_servers):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        try:
            await self.producer.start()
        except KafkaConnectionError:
            logger.error("Failed to connect to Kafka")
            await self.stop()
            raise ProducerConnectionError("Failed to connect to Kafka")
        logger.info("Kafka producer started")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def send_and_wait(self, topic, message):
        if not self.producer:
            raise ProducerError("Kafka producer is not started")
        try:
            await self.producer.send_and_wait(topic, message.encode("utf-8"))
        except KafkaError as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            raise ProducerError(f"Failed to send message to Kafka: {e}")
        else:
            logger.info(f"Message sent to Kafka topic [{topic}]: {message}")
