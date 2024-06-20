from fastapi import status
from fastapi.exceptions import ResponseValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from shared.utils.logger_utils import LoggerConfigurator

logger = LoggerConfigurator("middleware").configure()


class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal Server Error"},
        )

        try:
            response = await call_next(request)
        except ResponseValidationError as e:
            logger.error("Response validation error")
            for error in e.errors():
                logger.error(f"Field: {error['loc'][1]}, Error: {error['msg']}")
            if not e.errors():
                logger.error(f"Error: {e.body}, {e}")
        except Exception as exc:
            logger.error(f"Unhandled error: {exc}")
        finally:
            return response
