class CustomError(Exception):
    """Base class for custom exceptions"""

    pass


class DatabaseConnectionError(CustomError):
    """Exception raised for errors in the database connection."""

    def __init__(self, message="Could not connect to the database", details=None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class RepositoryError(CustomError):
    """Exception raised for errors in the database."""

    def __init__(self, message=None, details=None):
        self.message = message
        self.details = details
        super().__init__(self.message)
