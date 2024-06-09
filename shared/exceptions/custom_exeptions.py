class CustomError(Exception):
    """Base class for custom exceptions"""

    pass


class DatabaseConnectionError(CustomError):
    """Exception raised for errors in the database connection."""

    def __init__(self, message="Could not connect to the database"):
        self.message = message
        super().__init__(self.message)
