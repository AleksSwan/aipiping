class CustomError(Exception):
    """Base class for custom errors."""

    pass


class UIDNotFoundError(CustomError):
    """Exception raised for uid not found."""

    def __init__(self, message="UID not found", details=None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class CreateRecommendationError(CustomError):
    """Exception raised for create recommendation error."""

    def __init__(self, message="Create recommendation error", details=None):
        self.message = message
        self.details = details
        super().__init__(self.message)

class TaskNotCompletedError(CustomError):
    """Exception raised for uid not found."""

    def __init__(self, message="Task not completed", details=None):
        self.message = message
        self.details = details
        super().__init__(self.message)