# errors.py
class CustomError(Exception):
    """
    Base class for custom errors.
    """

    pass


class ProducerError(CustomError):
    """
    Generic exception for producer errors.
    """

    def __init__(self, message=None, details=None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class ProducerConnectionError(CustomError):
    """
    Exception raised for connection errors.
    """

    def __init__(self, message=None, details=None):
        self.message = message
        self.details = details
        super().__init__(self.message)
