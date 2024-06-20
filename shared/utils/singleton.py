from typing import Any, Dict, Type

from shared.utils.logger_utils import LoggerConfigurator

logger = LoggerConfigurator(name="singleton").configure()


class Singleton(type):
    """
    Singleton metaclass.

    This metaclass ensures that only one instance of a class is created, and
    provides a global point of access to that instance.

    """

    _instances: Dict[Any, Type["Singleton"]] = {}

    def __call__(cls: Any, *args, **kwargs):
        """
        Returns the instance of the class.

        If the instance does not exist, it creates a new one.

        Parameters
        ----------
        *args, **kwargs
            Arguments to pass to the constructor of the class.

        Returns
        -------
        instance
            The instance of the class.

        """
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            logger.debug(f"Created instance of {cls.__name__}")
        else:
            logger.debug(f"Reusing instance of {cls.__name__}")
            logger.debug(cls._instances[cls])
        return cls._instances[cls]
