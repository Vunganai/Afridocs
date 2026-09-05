"""
Custom application exceptions and global exception handlers.
"""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class AfriDocsError(Exception):
    """Base application exception."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(AfriDocsError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class ForbiddenError(AfriDocsError):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."


class ValidationError(AfriDocsError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation failed."


class ConflictError(AfriDocsError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists."


class UploadError(AfriDocsError):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "File upload failed."


class ProcessingError(AfriDocsError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Document processing failed."


class ExternalServiceError(AfriDocsError):
    status_code = status.HTTP_502_BAD_GATEWAY
    detail = "External service request failed."


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(AfriDocsError)
    async def afridocs_error_handler(request: Request, exc: AfriDocsError) -> JSONResponse:
        logger.warning(
            "application_error",
            error_type=type(exc).__name__,
            detail=exc.detail,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_error",
            error_type=type(exc).__name__,
            detail=str(exc),
            path=str(request.url),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An internal server error occurred."},
        )
